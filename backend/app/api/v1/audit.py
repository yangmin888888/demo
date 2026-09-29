import csv
import io
import logging
import urllib.parse
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import deps
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogListOut
from app.services.audit_service import ACTION_LABELS, TABLE_LABELS, field_label, serialize_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])

# 导出走全量行 + 内存拼装 CSV，必须设上限防止数据量增长后 OOM
EXPORT_MAX_ROWS = 50_000


def _build_query(
    table_name: str | None,
    action: str | None,
    username: str | None,
    record_id: int | None,
    start_time: datetime | None,
    end_time: datetime | None,
):
    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    if action:
        query = query.where(AuditLog.action == action)
    if username:
        query = query.where(AuditLog.username.like(f"%{username}%"))
    if record_id is not None:
        query = query.where(AuditLog.record_id == record_id)
    if start_time:
        query = query.where(AuditLog.created_at >= start_time)
    if end_time:
        query = query.where(AuditLog.created_at <= end_time)
    return query


@router.get("/tables", summary="可审计的表列表")
def list_tables(_: User = Depends(deps.get_current_superuser)):
    return sorted(TABLE_LABELS.keys())


@router.get("", response_model=AuditLogListOut, summary="审计日志查询")
def list_audit_logs(
    _: User = Depends(deps.get_current_superuser),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=200),
    table_name: str | None = Query(None, description="表名"),
    action: str | None = Query(None, description="insert/update/delete"),
    username: str | None = Query(None, description="操作人"),
    record_id: int | None = Query(None, description="记录主键"),
    start_time: datetime | None = Query(None, description="起始时间"),
    end_time: datetime | None = Query(None, description="截止时间"),
    db: Session = Depends(deps.get_db),
):
    query = _build_query(table_name, action, username, record_id, start_time, end_time)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)).all()
    return AuditLogListOut(total=total, items=items)


@router.get("/export", summary="导出审计日志 CSV")
def export_audit_logs(
    _: User = Depends(deps.get_current_superuser),
    table_name: str | None = Query(None),
    action: str | None = Query(None),
    username: str | None = Query(None),
    record_id: int | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    limit: int = Query(EXPORT_MAX_ROWS, ge=1, le=EXPORT_MAX_ROWS, description="导出最大条数"),
    db: Session = Depends(deps.get_db),
):
    query = _build_query(table_name, action, username, record_id, start_time, end_time).order_by(AuditLog.id)
    matched = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    if matched > limit:
        logger.warning("审计日志导出被截断：命中 %s 条，超过上限 %s 条，仅导出最早的 %s 条", matched, limit, limit)
    rows = db.scalars(query.limit(limit)).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["时间", "操作类型", "表", "记录ID", "操作人", "修改字段", "修改前", "修改后", "操作ID"])
    for row in rows:
        writer.writerow(
            [
                row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ACTION_LABELS.get(row.action, row.action),
                TABLE_LABELS.get(row.table_name, row.table_name),
                row.record_id or "",
                row.username,
                field_label(row.table_name, row.field_name),
                str(serialize_json(row.old_value)).replace("\n", " "),
                str(serialize_json(row.new_value)).replace("\n", " "),
                row.operation_id,
            ]
        )

    csv_bytes = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    filename = f"audit_logs_{datetime.now():%Y%m%d%H%M}.csv"
    quoted = urllib.parse.quote(filename)
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )