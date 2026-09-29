from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """当前 UTC 时间，带时区。"""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """统一以 UTC 存取的时间列。

    为什么需要它：SQLite 的 ``CURRENT_TIMESTAMP`` 是 UTC，MySQL 的 ``now()`` 是
    服务器本地时区，同一句 ``server_default=func.now()`` 换个库就是另一个时刻。
    SQLite 和 MySQL 的 ``DATETIME`` 本身也不带时区信息，写进去的偏移量会被
    直接丢弃，事后无从判断那串数字到底是哪个时区的墙钟时间。

    这里把语义固定下来——

    - 写入：naive 值按 UTC 解释，带偏移的值先折算成 UTC，然后**剥掉 tzinfo**，
      保证落到库里的永远是 UTC 墙钟时间，与库中既有数据、历史导出文件完全兼容。
    - 读出：一律补上 ``timezone.utc``，让应用层拿到的永远是 aware 的 UTC 时间，
      不需要再猜这个 naive 值属于哪个时区。

    默认值用 Python 侧的 ``default=utcnow``，不再用 ``server_default=func.now()``：
    前者由应用写入，与数据库方言无关。既有表里残留的 server default 不会再触发
    （每条 INSERT 都显式带上了该列），因此改这里不需要重建表。
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
