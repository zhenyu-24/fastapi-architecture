from datetime import datetime
from typing import Any, Protocol

from starlette_context.ctx import _Context, context
from starlette_context.errors import ContextDoesNotExistError


class TypedContextProtocol(Protocol):
    perf_time: float
    start_time: datetime

    ip: str
    country: str | None
    region: str | None
    city: str | None

    user_agent: str | None
    os: str | None
    browser: str | None
    device: str | None

    permission: str | None
    language: str

    user_id: int | None
    is_superuser: bool


class TypedContext(TypedContextProtocol, _Context):
    def __getattr__(self, name: str) -> Any:
        try:
            return context.get(name)
        except ContextDoesNotExistError:
            return None

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            context[name] = value
        except ContextDoesNotExistError:
            pass


ctx = TypedContext()
