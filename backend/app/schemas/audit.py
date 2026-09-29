from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: str
    table_name: str
    record_id: int | None = None
    action: str
    user_id: int | None = None
    username: str
    field_name: str | None = None
    old_value: dict | list | str | int | float | None = None
    new_value: dict | list | str | int | float | None = None
    created_at: datetime


class AuditLogListOut(BaseModel):
    total: int
    items: list[AuditLogOut]