"""Run once before restarting API/Worker: uv run python -m backend.plugin.files.migrate_references."""

import asyncio

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection

from backend.app.admin.model.user import User
from backend.database.db import async_db_session, async_engine
from backend.plugin.files.model import FileRecord, FileReference
from backend.plugin.files.service.reference_service import reference_service
from backend.utils.snowflake import snowflake
from backend.utils.timezone import timezone


def upgrade_schema(connection: Connection) -> bool:
    """幂等增加结构，旧文件默认长期保留，不推断未知业务用途。"""
    columns = {column['name'] for column in inspect(connection).get_columns('sys_file_record')}
    first_upgrade = 'retention_policy' not in columns
    if first_upgrade:
        connection.execute(
            text("ALTER TABLE sys_file_record ADD COLUMN retention_policy VARCHAR(16) NOT NULL DEFAULT 'persistent'")
        )
    if 'unreferenced_at' not in columns:
        connection.execute(text('ALTER TABLE sys_file_record ADD COLUMN unreferenced_at TIMESTAMP NULL'))
    FileReference.__table__.create(connection, checkfirst=True)
    return first_upgrade


async def migrate() -> None:
    async with async_engine.begin() as connection:
        first_upgrade = await connection.run_sync(upgrade_schema)
    await snowflake.init()
    try:
        async with async_db_session.begin() as db:
            sources = [
                ('user', user.id, 'avatar', user.avatar)
                for user in (await db.scalars(select(User).where(User.deleted == 0, User.avatar.is_not(None)))).all()
            ]
            async with async_engine.connect() as connection:
                has_links = await connection.run_sync(lambda conn: inspect(conn).has_table('sys_external_link'))
            if has_links:
                from backend.plugin.external_links.model import ExternalLink

                sources.extend(
                    ('external_link', link.id, 'icon', link.icon)
                    for link in (await db.scalars(select(ExternalLink).where(ExternalLink.deleted == 0))).all()
                )
            for business, business_id, field, value in sources:
                record = await reference_service.resolve(db=db, value=value or '', strict=False)
                if record is None:
                    continue
                await reference_service.sync(
                    db=db, business_type=business, business_id=business_id, field=field, value=value
                )
                if first_upgrade:
                    record.retention_policy = 'temporary'
            # 可确认头像用途；其余旧文件不凭文件名猜测是否可删除。
            avatars = (await db.scalars(select(FileRecord).where(FileRecord.upload_type == 'avatar'))).all()
            for record in avatars:
                record.retention_policy = 'temporary'
                if not await reference_service.is_referenced(db=db, file_id=record.id):
                    record.unreferenced_at = record.unreferenced_at or timezone.now()
            print(f'File reference migration complete; checked {len(sources)} business fields.')
    finally:
        await snowflake.shutdown()
        await async_engine.dispose()


if __name__ == '__main__':
    asyncio.run(migrate())
