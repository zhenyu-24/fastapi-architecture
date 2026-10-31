from datetime import datetime, timedelta

from sqlalchemy import Select, Table, delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.utils.dynamic_import import get_all_models
from backend.utils.timezone import timezone

# 文件记录必须由文件清理服务处理，避免磁盘文件失去追踪。
EXCLUDED_TABLES = frozenset({'sys_file_record'})

# 父记录仍有关联数据时保留，避免物理删除后留下逻辑悬空引用。
REFERENCES = {
    'sys_user': (('sys_user_social', 'user_id'),),
    'sys_dept': (('sys_user', 'dept_id'), ('sys_dept', 'parent_id')),
    'sys_menu': (('sys_menu', 'parent_id'),),
    'sys_dict_type': (('sys_dict_data', 'type_id'),),
}

# 纯关联及附属数据随父记录一起清理，不删除其关联的其他业务实体。
DEPENDENTS = {
    'sys_user': (
        ('sys_user_role', 'user_id'),
        ('sys_user_password_history', 'user_id'),
        ('sys_user_notice', 'user_id'),
    ),
    'sys_role': (('sys_user_role', 'role_id'), ('sys_role_menu', 'role_id'), ('sys_role_data_scope', 'role_id')),
    'sys_menu': (('sys_role_menu', 'menu_id'),),
    'sys_data_scope': (('sys_role_data_scope', 'data_scope_id'), ('sys_data_scope_rule', 'data_scope_id')),
    'sys_data_rule': (('sys_data_scope_rule', 'data_rule_id'),),
    'sys_notice': (('sys_user_notice', 'notice_id'),),
    'code_gen_business': (('code_gen_column', 'code_gen_business_id'),),
}


class SoftDeleteService:
    """分批回收超过保留期的软删除数据。"""

    @staticmethod
    def get_tables() -> dict[str, Table]:
        get_all_models()
        from backend.common.model import MappedBase

        return {table.name: table for table in MappedBase.metadata.tables.values()}

    @staticmethod
    def reference_conditions(*, table: Table, tables: dict[str, Table]) -> list:
        """返回阻止父记录删除的引用条件，涵盖逻辑关联及真实外键。"""
        conditions = []
        dependents = DEPENDENTS.get(table.name, ())
        for child_name, column in REFERENCES.get(table.name, ()):
            if child_name in tables:
                child = tables[child_name].alias()
                conditions.append(exists(select(1).where(child.c[column] == table.c.id)))
        for child_table in tables.values():
            for constraint in child_table.foreign_key_constraints:
                if constraint.referred_table is not table or (constraint.ondelete or '').upper() == 'SET NULL':
                    continue
                if all((child_table.name, fk.parent.name) in dependents for fk in constraint.elements):
                    continue
                child = child_table.alias()
                conditions.append(
                    exists(
                        select(1).where(
                            *(child.c[fk.parent.name] == table.c[fk.column.name] for fk in constraint.elements)
                        )
                    )
                )
        return conditions

    @staticmethod
    def get_purge_tables(*, tables: dict[str, Table]) -> list[Table]:
        """自动发现软删除表，并按真实外键及逻辑关联安排子表优先。"""
        eligible = {
            name: table
            for name, table in tables.items()
            if name not in EXCLUDED_TABLES
            and {'id', 'deleted', 'deleted_time'}.issubset(table.c.keys())
            and list(table.primary_key.columns) == [table.c.id]
        }
        children: dict[str, set[str]] = {name: set() for name in eligible}
        for name, table in eligible.items():
            for fk in table.foreign_keys:
                parent = fk.column.table.name
                if parent in children:
                    children[parent].add(name)
            children[name].update(child for child, _ in REFERENCES.get(name, ()) if child in eligible)
        ordered: list[Table] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            # 环形引用仍由引用条件保护，不尝试强制解除关联。
            if name in visited:
                return
            visited.add(name)
            for child in sorted(children[name]):
                visit(child)
            ordered.append(eligible[name])

        for name in sorted(eligible):
            visit(name)
        return ordered

    @staticmethod
    def candidates(*, table: Table, tables: dict[str, Table], cutoff: datetime, after_id: int) -> Select:
        statement = select(table.c.id).where(
            table.c.deleted != 0,
            table.c.deleted_time.is_not(None),
            table.c.deleted_time <= cutoff,
            table.c.id > after_id,
        )
        for condition in SoftDeleteService.reference_conditions(table=table, tables=tables):
            statement = statement.where(~condition)
        return (
            statement
            .order_by(table.c.id)
            .limit(settings.SOFT_DELETE_CLEANUP_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )

    @staticmethod
    async def delete_batch(
        *, db: AsyncSession, table: Table, tables: dict[str, Table], ids: list[int], cutoff: datetime
    ) -> int:
        for child_name, column in DEPENDENTS.get(table.name, ()):
            if child_name in tables:
                child = tables[child_name]
                await db.execute(delete(child).where(child.c[column].in_(ids)))
        result = await db.execute(
            delete(table).where(table.c.id.in_(ids), table.c.deleted != 0, table.c.deleted_time <= cutoff)
        )
        return result.rowcount

    async def cleanup(self) -> dict[str, int]:
        cutoff = timezone.now() - timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS)
        tables = self.get_tables()
        counts: dict[str, int] = {}
        for table in self.get_purge_tables(tables=tables):
            name = table.name
            after_id = 0
            while True:
                async with async_db_session.begin() as db:
                    statement = self.candidates(table=table, tables=tables, cutoff=cutoff, after_id=after_id)
                    ids = list((await db.scalars(statement)).all())
                    if not ids:
                        break
                    count = await self.delete_batch(db=db, table=table, tables=tables, ids=ids, cutoff=cutoff)
                counts[name] = counts.get(name, 0) + count
                after_id = ids[-1]
        return counts


soft_delete_service = SoftDeleteService()
