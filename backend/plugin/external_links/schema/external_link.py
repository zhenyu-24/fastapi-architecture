from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import ConfigDict, Field, field_serializer, model_validator

from backend.common.schema import SchemaBase


class ExternalLinkParam(SchemaBase):
    """外部页面配置参数"""

    title: str = Field(min_length=1, max_length=100, description='名称')
    kind: Literal['group', 'link'] = Field(description='分类或链接')
    parent_id: int | None = Field(None, gt=0, description='父分类 ID')
    url: str = Field('', max_length=2048, description='HTTP/HTTPS 地址')
    open_mode: Literal['iframe', 'external'] = Field('iframe', description='内嵌或新窗口')
    display_mode: Literal['menu', 'buttons'] = Field('menu', description='多级菜单或分类按钮')
    icon: str = Field('', max_length=100, description='图标')
    description: str = Field('', max_length=500, description='描述')
    sort: int = Field(0, ge=0, le=999999, description='排序')
    enabled: bool = Field(True, description='是否启用')

    @model_validator(mode='after')
    def validate_content(self) -> Self:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError('名称不能为空')
        self.url = self.url.strip()
        if self.kind == 'link':
            try:
                parsed = urlsplit(self.url)
                valid = (
                    parsed.scheme in {'http', 'https'}
                    and parsed.hostname
                    and not parsed.username
                    and not parsed.password
                    and not any(char.isspace() or ord(char) < 32 for char in self.url)
                    and '\\' not in self.url
                )
                parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise ValueError('请输入有效的 HTTP/HTTPS 地址，地址中不能包含账号密码')
        else:
            self.url = ''
        return self


class GetExternalLinkDetail(ExternalLinkParam):
    """外部页面配置详情，ID 以字符串传输以兼容雪花主键"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='记录 ID')

    @field_serializer('id', 'parent_id')
    def serialize_id(self, value: int | None) -> str | None:
        return str(value) if value is not None else None
