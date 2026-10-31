from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_serializer, validate_email

from backend.utils.identifiers import stringify_ids
from backend.utils.timezone import timezone

CustomPhoneNumber = Annotated[str, Field(pattern=r'^1[3-9]\d{9}$')]


class CustomEmailStr(EmailStr):
    """自定义邮箱类型"""

    @classmethod
    def _validate(cls, input_value: str, /) -> str | None:
        return None if not input_value else validate_email(input_value)[1]


class SchemaBase(BaseModel):
    """基础模型配置"""

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda x: (
                timezone.to_str(timezone.from_datetime(x))
                if x.tzinfo is not None and x.tzinfo != timezone.tz_info
                else timezone.to_str(x)
            ),
        },
    )

    @model_serializer(mode='wrap', when_used='json')
    def serialize_identifiers(self, handler: Any) -> Any:
        return stringify_ids(handler(self))


def ser_string(value: Any) -> str | None:
    if value:
        return str(value)
    return value
