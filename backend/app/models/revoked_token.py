from datetime import datetime

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, utcnow


class RevokedToken(Base):
    """已撤销的访问令牌。

    JWT 本身无状态，服务端无法"删除"一个已签发的 token。登出时把 token 的
    jti 登记到这里，鉴权时拒绝命中该表的 token，从而实现真正的登出失效。

    expires_at 存的是 token 自身的过期时间：过期后该记录失去意义，
    由 init_db 的清理逻辑回收，避免表无限增长。

    时间列统一用 UTCDateTime：写库存 UTC 墙钟时间，读出来带 UTC 时区。
    """

    __tablename__ = "revoked_tokens"
    __table_args__ = (
        Index("ix_revoked_expires", "expires_at"),
        Index("ix_revoked_jti", "jti", unique=True),
    )

    # 与其他实体表保持一致的自增主键：审计服务按主键记录 record_id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, comment="token 的 jti 声明")
    user_id: Mapped[int | None] = mapped_column(comment="被撤销 token 所属用户")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, comment="token 自身过期时间（UTC）")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False, comment="撤销时间（UTC）"
    )
