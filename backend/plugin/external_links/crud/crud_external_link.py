from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.external_links.model import ExternalLink
from backend.plugin.external_links.schema.external_link import ExternalLinkParam


class CRUDExternalLink(CRUDPlus[ExternalLink]):
    """外部页面数据库操作"""

    async def get_all(self, db: AsyncSession, *, lock: bool = False) -> Sequence[ExternalLink]:
        statement = select(self.model).where(self.model.deleted == 0).order_by(self.model.sort, self.model.id)
        if lock:
            statement = statement.with_for_update()
        return (await db.scalars(statement)).all()

    async def create(self, db: AsyncSession, obj: ExternalLinkParam) -> ExternalLink:
        row = self.model(**obj.model_dump())
        db.add(row)
        await db.flush()
        return row

    async def update(self, db: AsyncSession, row: ExternalLink, obj: ExternalLinkParam) -> None:
        for key, value in obj.model_dump().items():
            setattr(row, key, value)
        await db.flush()


external_link_dao = CRUDExternalLink(ExternalLink)
