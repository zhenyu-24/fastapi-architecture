#!/bin/sh
set -eu

cd /fba

python - <<'PY'
import asyncio
import importlib

from sqlalchemy import inspect

from backend.app.admin import model as _admin_models
from backend.app.task import model as _task_models
from backend.cli import execute_sql_scripts, get_sql_scripts
from backend.common.model import MappedBase
from backend.core.path_conf import PLUGIN_DIR
from backend.database.db import async_db_session, async_engine
from backend.plugin.core import get_plugins


async def main() -> None:
    for plugin in get_plugins():
        model_init = PLUGIN_DIR / plugin / "model" / "__init__.py"
        if model_init.exists():
            importlib.import_module(f"backend.plugin.{plugin}.model")

    async with async_engine.begin() as connection:
        initialized = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).has_table("sys_user")
        )
        if initialized:
            print("fba database already initialized", flush=True)
            return
        await connection.run_sync(MappedBase.metadata.create_all)

    async with async_db_session.begin() as session:
        for sql_script in await get_sql_scripts():
            await execute_sql_scripts(session, sql_script, is_init=True)

    print("fba database initialized", flush=True)


asyncio.run(main())
PY

exec supervisord -c /etc/supervisor/supervisord.conf
