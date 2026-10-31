import asyncio
import importlib
import itertools
import os

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapper

from backend.common.exception import errors
from backend.plugin.files.model import FileRecord, FileReference
from backend.plugin.files.service.reference_service import reference_service
from backend.utils.timezone import timezone


def test_reference_lifecycle_and_cleanup(tmp_path: Path) -> None:
    asyncio.run(run_lifecycle(tmp_path))


async def run_lifecycle(root: Path) -> None:
    engine = create_async_engine('sqlite+aiosqlite://')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    sequence = itertools.count(100)

    def assign_id(mapper: Mapper, connection: Connection, target: FileReference) -> None:
        target.id = next(sequence)

    event.listen(FileReference, 'before_insert', assign_id)
    try:
        async with engine.begin() as connection:
            await connection.execute(text('CREATE TABLE sys_user (id BIGINT PRIMARY KEY)'))
            await connection.run_sync(FileRecord.__table__.create)
            await connection.run_sync(FileReference.__table__.create)
        async with sessions.begin() as db:
            for index, policy in [(1, 'temporary'), (2, 'temporary'), (3, 'persistent'), (4, 'temporary')]:
                path = root / 'public' / 'image' / f'{index}.png'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
                record = FileRecord(
                    name=path.name,
                    original_name=path.name,
                    extension='png',
                    upload_type='image',
                    size=7,
                    url_path=f'/static/upload/public/image/{path.name}',
                    retention_policy=policy,
                    unreferenced_at=timezone.now() - timedelta(days=2),
                )
                record.id = index
                db.add(record)
        async with sessions.begin() as db:
            for business_id in [10, 11]:
                await reference_service.sync(
                    db=db,
                    business_type='external_link',
                    business_id=business_id,
                    field='icon',
                    value='/static/upload/public/image/1.png',
                )
            # Retry must not duplicate a reference.
            await reference_service.sync(
                db=db,
                business_type='external_link',
                business_id=10,
                field='icon',
                value='/static/upload/public/image/1.png',
            )
            assert len((await db.scalars(select(FileReference))).all()) == 2
            for business_id in [10, 11]:
                await reference_service.sync(
                    db=db,
                    business_type='external_link',
                    business_id=business_id,
                    field='icon',
                    value='/static/upload/public/image/2.png',
                )
                old = await db.get(FileRecord, 1)
                assert (old.unreferenced_at is None) == (business_id == 10)
            await reference_service.require_unused(db=db, file_id=1)
            try:
                await reference_service.require_unused(db=db, file_id=2)
            except errors.ConflictError:
                pass
            else:
                raise AssertionError('Referenced file must be protected')
            old.unreferenced_at = timezone.now() - timedelta(days=2)
            # An abandoned new upload remains in its protection period.
            recent = await db.get(FileRecord, 4)
            recent.unreferenced_at = timezone.now()
        cleanup = importlib.import_module('backend.plugin.files.service.cleanup_service')
        files = importlib.import_module('backend.plugin.files.service.file_service')
        with (
            patch.object(cleanup, 'UPLOAD_DIR', root),
            patch.object(files, 'UPLOAD_DIR', root),
            patch.object(cleanup, 'async_db_session', sessions),
        ):
            result = await cleanup.cleanup_service.cleanup()
            assert result.deleted_records == 1
            assert not (root / 'public/image/1.png').exists()
            for index in [2, 3, 4]:
                assert (root / f'public/image/{index}.png').exists()
            # Disk-only orphan reporting remains separate from record cleanup.
            orphan = root / 'untracked.txt'
            orphan.touch()
            os.utime(orphan, (0, 0))
            second = await cleanup.cleanup_service.cleanup()
            assert second.deleted_records == 0
            assert second.untracked_files == 1
        async with sessions.begin() as db:
            await reference_service.sync(db=db, business_type='external_link', business_id=10, field='icon', value='')
            assert await reference_service.is_referenced(db=db, file_id=2)
            await reference_service.sync(db=db, business_type='external_link', business_id=11, field='icon', value='')
            assert not await reference_service.is_referenced(db=db, file_id=2)
            assert (await db.get(FileRecord, 2)).unreferenced_at is not None
        async with sessions() as db:
            await reference_service.sync(
                db=db,
                business_type='external_link',
                business_id=12,
                field='icon',
                value='/static/upload/public/image/2.png',
            )
            await db.rollback()
        async with sessions() as db:
            assert not await reference_service.is_referenced(db=db, file_id=2)
            try:
                await reference_service.resolve(db=db, value='/static/upload/public/image/1.png')
            except errors.RequestError:
                pass
            else:
                raise AssertionError('Deleted local file must not be rebound')
    finally:
        event.remove(FileReference, 'before_insert', assign_id)
        await engine.dispose()
