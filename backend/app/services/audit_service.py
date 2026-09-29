import json
import uuid
from datetime import date, datetime

from sqlalchemy import event, inspect
from sqlalchemy.orm import Mapper, object_session

from app.core.audit_context import get_actor
from app.db.base import Base
from app.models.audit import AuditLog

# GMP 要求审计追踪不可关闭，审计表自身不参与审计
EXCLUDED_TABLES = {"audit_logs"}
# 系统维护的元数据字段不产生审计噪音
IGNORED_FIELDS = {"id", "created_at", "updated_at"}
# 敏感字段只记录"发生过变更"，不记录具体值，避免密码哈希进入审计表
REDACTED_FIELDS = {"hashed_password"}
REDACTED_PLACEHOLDER = "***"
# action 的中文描述，供前端展示
ACTION_LABELS: dict[str, str] = {"insert": "新增", "update": "修改", "delete": "删除"}
TABLE_LABELS: dict[str, str] = {"users": "用户", "revoked_tokens": "令牌撤销"}
# 字段名的中文描述，两级字典：表名 -> 字段名 -> 中文
FIELD_LABELS: dict[str, dict[str, str]] = {
    "users": {
        "username": "用户名",
        "email": "邮箱",
        "nickname": "昵称",
        "hashed_password": "登录密码",
        "is_active": "启用状态",
        "is_superuser": "管理员",
    },
    "revoked_tokens": {
        "jti": "令牌标识",
        "user_id": "用户ID",
        "expires_at": "令牌过期时间",
        "created_at": "撤销时间",
    },
}


def field_label(table_name: str | None, field_name: str | None) -> str:
    """把 (表名, 字段名) 翻译为中文，未登记的原样返回。"""
    if not field_name:
        return ""
    return FIELD_LABELS.get(table_name or "", {}).get(field_name, field_name)


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Base):
        return str(value)
    return value


def _column_data(target) -> dict:
    state = inspect(target)
    data = {}
    for prop in state.mapper.column_attrs:
        if prop.key in IGNORED_FIELDS:
            continue
        if prop.key in REDACTED_FIELDS:
            data[prop.key] = REDACTED_PLACEHOLDER
            continue
        try:
            value = getattr(target, prop.key)
        except Exception:
            continue
        if value is None:
            continue
        data[prop.key] = _serialize(value)
    return data


def _record_id(target) -> int | None:
    """取记录主键。不能硬编码 target.id——并非所有表都有 id 列。

    复合主键的表不产生 record_id（audit_logs.record_id 是单列整型，
    塞不进复合键值），这类表的新增/修改/删除将无法按记录 ID 追溯。
    """
    primary_key = inspect(target).mapper.primary_key
    if len(primary_key) != 1:
        return None
    value = getattr(target, primary_key[0].key, None)
    return value if isinstance(value, int) else None


def _emit(target, connection, operation_id: str, table: str, record_id, action: str, field: str | None, old, new) -> None:
    user_id, username = get_actor(object_session(target))
    connection.execute(
        AuditLog.__table__.insert().values(
            operation_id=operation_id,
            table_name=table,
            record_id=record_id,
            action=action,
            user_id=user_id,
            username=username or "system",
            field_name=field,
            old_value=old,
            new_value=new,
        )
    )


def _on_insert(mapper: Mapper, connection, target) -> None:
    if target.__tablename__ in EXCLUDED_TABLES:
        return
    # 必须挂在 after_insert 而非 before_insert：自增主键要等 INSERT 发出并取回
    # lastrowid / RETURNING 之后才会回填到 target 上，before_insert 阶段取不到，
    # 会让审计记录的 record_id 恒为 null
    _emit(
        target,
        connection,
        uuid.uuid4().hex,
        target.__tablename__,
        _record_id(target),
        "insert",
        "*",
        None,
        _column_data(target),
    )


def _on_update(mapper: Mapper, connection, target) -> None:
    if target.__tablename__ in EXCLUDED_TABLES:
        return
    state = inspect(target)
    record_id = _record_id(target)
    operation_id = uuid.uuid4().hex
    for prop in state.mapper.column_attrs:
        if prop.key in IGNORED_FIELDS:
            continue
        attr = state.attrs[prop.key]
        history = attr.history
        if not history.has_changes():
            continue
        old = _serialize(history.deleted[0]) if history.deleted else None
        new = _serialize(history.added[0]) if history.added else None
        if old == new:
            continue
        if prop.key in REDACTED_FIELDS:
            old = new = REDACTED_PLACEHOLDER
        _emit(target, connection, operation_id, target.__tablename__, record_id, "update", prop.key, old, new)


def _on_delete(mapper: Mapper, connection, target) -> None:
    if target.__tablename__ in EXCLUDED_TABLES:
        return
    _emit(
        target,
        connection,
        uuid.uuid4().hex,
        target.__tablename__,
        _record_id(target),
        "delete",
        "*",
        _column_data(target),
        None,
    )


def install_audit_listeners() -> None:
    """为所有 ORM 模型安装审计事件监听。在应用启动时调用一次。"""
    for mapper in Base.registry.mappers:
        if mapper.class_.__tablename__ in EXCLUDED_TABLES:
            continue
        event.listen(mapper, "after_insert", _on_insert)
        event.listen(mapper, "before_update", _on_update)
        event.listen(mapper, "before_delete", _on_delete)


def serialize_json(value) -> str:
    """将 JSON 列值转为可读字符串（前端/导出用）。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)