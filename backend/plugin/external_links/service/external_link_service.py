from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.external_links.crud.crud_external_link import external_link_dao
from backend.plugin.external_links.model import ExternalLink
from backend.plugin.external_links.schema.external_link import ExternalLinkParam
from backend.utils.timezone import timezone


class ExternalLinkService:
    """外部页面配置与发布"""

    @staticmethod
    async def get_all(*, db: AsyncSession, published: bool = False) -> Sequence[ExternalLink]:
        rows = await external_link_dao.get_all(db)
        if not published:
            return rows
        by_id = {row.id: row for row in rows}

        def is_visible(row: ExternalLink) -> bool:
            seen: set[int] = set()
            while True:
                if not row.enabled or row.id in seen:
                    return False
                seen.add(row.id)
                if row.parent_id is None:
                    return True
                parent = by_id.get(row.parent_id)
                if parent is None or parent.kind != 'group':
                    return False
                row = parent

        return [row for row in rows if is_visible(row)]

    @staticmethod
    async def save(*, db: AsyncSession, obj: ExternalLinkParam, pk: int | None = None) -> ExternalLink:
        # Lock the configuration tree so concurrent moves cannot create a cycle.
        rows = await external_link_dao.get_all(db, lock=True)
        by_id = {row.id: row for row in rows}
        row = by_id.get(pk)
        if pk is not None and row is None:
            raise errors.NotFoundError(msg='外部页面不存在')
        if obj.kind == 'link' and any(item.parent_id == pk for item in rows) and pk is not None:
            raise errors.RequestError(msg='请先移走子项，再将分类改为链接')
        parent_id = obj.parent_id
        seen = {pk}
        while parent_id is not None:
            if parent_id in seen:
                raise errors.RequestError(msg='不能将分类移动到自身或子分类下')
            seen.add(parent_id)
            parent = by_id.get(parent_id)
            if parent is None or parent.kind != 'group':
                raise errors.RequestError(msg='父分类不存在或不是分类')
            parent_id = parent.parent_id
        if row is None:
            row = await external_link_dao.create(db, obj)
        else:
            await external_link_dao.update(db, row, obj)
        from backend.plugin.files.service.reference_service import reference_service

        await reference_service.sync(
            db=db, business_type='external_link', business_id=row.id, field='icon', value=row.icon
        )
        return row

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> None:
        rows = await external_link_dao.get_all(db, lock=True)
        row = next((item for item in rows if item.id == pk), None)
        if row is None:
            raise errors.NotFoundError(msg='外部页面不存在')
        if any(item.parent_id == pk for item in rows):
            raise errors.RequestError(msg='请先删除或移走该分类下的子项')
        row.deleted = row.id
        row.deleted_time = timezone.now()
        from backend.plugin.files.service.reference_service import reference_service

        await reference_service.sync(
            db=db, business_type='external_link', business_id=row.id, field='icon', value=''
        )
        await db.flush()


external_link_service = ExternalLinkService()
