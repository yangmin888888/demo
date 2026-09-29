from datetime import datetime

from sqlalchemy import Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, utcnow


class AuditLog(Base):
    """审计日志（GMP 审计追踪）。

    只追加、只读：任何接口都不提供修改/删除，数据库层面禁止一切对该表的写操作。
    """

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_table_record", "table_name", "record_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="一次操作唯一标识（ORID）")
    table_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False, comment="表名")
    record_id: Mapped[int | None] = mapped_column(Integer, comment="记录主键")
    action: Mapped[str] = mapped_column(String(16), index=True, nullable=False, comment="insert/update/delete")
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, comment="操作人 ID")
    username: Mapped[str] = mapped_column(String(64), index=True, default="system", comment="操作人账号")
    field_name: Mapped[str | None] = mapped_column(String(64), comment="变更字段（update 时），insert/delete 为 *")
    old_value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, comment="修改前值")
    new_value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, comment="修改后值")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True, nullable=False)