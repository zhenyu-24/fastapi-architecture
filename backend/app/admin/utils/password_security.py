from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_user_password_history import user_password_history_dao
from backend.app.admin.schema.user import GetPasswordPolicy
from backend.common.exception import errors
from backend.core.conf import settings
from backend.utils.dynamic_config import load_user_security_config
from backend.utils.pattern_validate import is_has_special_char

password_hash = PasswordHash((BcryptHasher(),))


def get_hash_password(password: str, salt: bytes | None) -> str:
    """
    使用哈希算法加密密码

    :param password: 密码
    :param salt: 盐值
    :return:
    """
    return password_hash.hash(password, salt=salt)


def password_verify(plain_password: str, hashed_password: str) -> bool:
    """
    密码验证

    :param plain_password: 待验证的密码
    :param hashed_password: 哈希密码
    :return:
    """
    return password_hash.verify(plain_password, hashed_password)


async def get_password_policy(db: AsyncSession) -> GetPasswordPolicy:
    """读取当前生效的公开密码规则"""
    await load_user_security_config(db)
    return GetPasswordPolicy(
        min_length=settings.USER_PASSWORD_MIN_LENGTH,
        max_length=settings.USER_PASSWORD_MAX_LENGTH,
        require_special_char=settings.USER_PASSWORD_REQUIRE_SPECIAL_CHAR,
    )


async def validate_new_password(db: AsyncSession, user_id: int | None, new_password: str) -> None:
    """
    验证新密码

    :param db: 数据库会话
    :param user_id: 用户 ID，注册时传入 None，跳过历史密码检查
    :param new_password: 新密码
    :return:
    """
    policy = await get_password_policy(db)

    if len(new_password) < policy.min_length:
        raise errors.RequestError(msg=f'密码长度不能少于 {policy.min_length} 个字符')

    if len(new_password) > policy.max_length:
        raise errors.RequestError(msg=f'密码长度不能超过 {policy.max_length} 个字符')

    if policy.require_special_char and not is_has_special_char(new_password):
        raise errors.RequestError(msg='密码必须包含特殊字符（如：!@#$%）')

    if user_id is None:
        return

    password_history = await user_password_history_dao.get_by_user_id(db, user_id)

    for hist in password_history[: settings.USER_PASSWORD_HISTORY_CHECK_COUNT]:
        if password_verify(new_password, hist.password):
            raise errors.RequestError(
                msg=f'新密码不能与最近 {settings.USER_PASSWORD_HISTORY_CHECK_COUNT} 次使用的密码相同'
            )
