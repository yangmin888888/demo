import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, purge_expired_revocations
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_ADMIN = {
    "username": "admin",
    "email": "admin@example.com",
    "password": "admin123",
    "nickname": "超级管理员",
}


def init_db(db: Session) -> None:
    """初始化数据库：建表、清理过期的令牌撤销记录并写入种子管理员账号。"""
    from app.db.base import Base
    from app.db.session import engine

    Base.metadata.create_all(bind=engine)

    purged = purge_expired_revocations(db)
    if purged:
        logger.info("已清理 %s 条过期的令牌撤销记录", purged)

    exists = db.scalar(select(User).where(User.username == DEFAULT_ADMIN["username"]))
    if exists:
        return
    db.add(
        User(
            username=DEFAULT_ADMIN["username"],
            email=DEFAULT_ADMIN["email"],
            nickname=DEFAULT_ADMIN["nickname"],
            hashed_password=hash_password(DEFAULT_ADMIN["password"]),
            is_active=True,
            is_superuser=True,
        )
    )
    db.commit()
    logger.info("已创建默认管理员账号 %s，请立即登录并修改初始密码", DEFAULT_ADMIN["username"])
