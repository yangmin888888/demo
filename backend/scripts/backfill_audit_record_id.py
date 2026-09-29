"""一次性回填脚本：修复 insert 审计记录 record_id 为 null 的历史数据。

背景：`audit_service._on_insert` 早期挂在 `before_insert`，此时自增主键尚未
回填到 target 上，导致所有 insert 审计记录的 record_id 都是 null。该问题已在
`after_insert` 改动中修复，但**存量数据不会自动补齐**，需运行本脚本。

匹配依据：insert 快照的 new_value 里带有 username（已脱敏的 hashed_password
不影响匹配），按 username 关联 users.id。

用法：
    python -m scripts.backfill_audit_record_id            # 演练，只统计不改库
    python -m scripts.backfill_audit_record_id --apply    # 实际写库
"""

import argparse
import logging
import os
import sys

# 允许以 `python scripts/backfill_audit_record_id.py` 直接运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.user import User  # noqa: E402

logger = logging.getLogger("backfill_audit_record_id")

# 目前只有 users 一张业务表；新增业务表时在此登记"用哪个字段做关联"
BACKFILL_RULES: dict[str, str] = {"users": "username"}


def backfill(db: Session, apply: bool) -> int:
    total = 0
    per_table: dict[str, dict[str, int]] = {}

    for table_name, key in BACKFILL_RULES.items():
        rows = db.scalars(
            select(AuditLog).where(
                AuditLog.table_name == table_name,
                AuditLog.action == "insert",
                AuditLog.record_id.is_(None),
            )
        ).all()
        matched = unmatched = 0
        for row in rows:
            snapshot = row.new_value if isinstance(row.new_value, dict) else {}
            name = snapshot.get(key)
            if not name:
                unmatched += 1
                continue
            user = db.scalar(select(User).where(User.username == name))
            if user is None:
                unmatched += 1
                continue
            matched += 1
            if apply:
                row.record_id = user.id
        if apply and matched:
            db.commit()
        total += matched
        per_table[table_name] = {"matched": matched, "unmatched": unmatched}
        logger.info(
            "表 %s：可回填 %s 条，无法匹配 %s 条%s",
            table_name,
            matched,
            unmatched,
            "（已写库）" if apply and matched else "",
        )

    if not apply:
        logger.info("以上为演练结果，未修改数据库。确认无误后加 --apply 执行。")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="回填 insert 审计记录的 record_id")
    parser.add_argument("--apply", action="store_true", help="实际写库；缺省为演练")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    db = SessionLocal()
    try:
        pending = db.scalar(
            select(AuditLog).with_only_columns(AuditLog.id).where(
                AuditLog.action == "insert", AuditLog.record_id.is_(None)
            ).limit(1)
        )
        if pending is None:
            logger.info("没有需要回填的记录。")
            return 0
        backfill(db, apply=args.apply)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
