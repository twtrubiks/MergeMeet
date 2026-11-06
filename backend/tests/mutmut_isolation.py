"""mutmut 平行變異測試的資源隔離（pytest plugin）

mutmut 會 fork 多個 worker 同時跑測試，但本專案測試共用同一個 PostgreSQL 測試庫
（每個測試 create_all / drop_all，session fixture 還會 pg_terminate_backend 其他連線）
與同一個 Redis，平行執行會互相干擾。

此 plugin 讓每個 pytest session 以 flock 取得一個獨佔 slot：
- PostgreSQL：改用 ``<測試庫>_mm<slot>``（不存在時自動建立）
- Redis：改用 db ``<slot + 1>``（db 0 保留給一般開發）

worker 結束（含逾時被 kill）時 fd 關閉，flock 自動釋放。

另需搭配 ``process_isolation = "forkserver"``：預設的 fork 模式會在同一個行程裡
連續跑多次 pytest session，ContentModerationService 等單例持有的 Redis 連線
會綁在上一個 session 已關閉的 event loop 上（Event loop is closed）。

僅供 mutmut 使用（pyproject.toml 的 ``[tool.mutmut]`` 以 ``-p tests.mutmut_isolation`` 載入），
一般 ``pytest`` 不會載入此模組。
"""

import fcntl
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, text

MAX_SLOTS = 15  # Redis 預設 16 個 db，db 0 保留
LOCK_DIR = Path(tempfile.gettempdir()) / "mergemeet-mutmut-slots"

_lock_fd: int | None = None


def _acquire_slot() -> int:
    global _lock_fd
    LOCK_DIR.mkdir(exist_ok=True)
    for slot in range(MAX_SLOTS):
        fd = os.open(LOCK_DIR / f"slot{slot}.lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            continue
        _lock_fd = fd
        return slot
    raise RuntimeError(f"mutmut 隔離 slot 已滿（{MAX_SLOTS}），請降低 --max-children")


def _with_path(url: str, path: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path=path))


def _ensure_database(base_sync_url: str, db_name: str) -> None:
    # 連到 postgres 維護庫：若連到測試庫，同時執行的一般 pytest 會
    # pg_terminate_backend 掉這條連線
    engine = create_engine(_with_path(base_sync_url, "/postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


def _drop_leftover_tables(sync_url: str) -> None:
    """清掉逾時被 kill 的 worker 可能殘留的資料表"""
    from app.core.database import Base

    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid != pg_backend_pid()"
            )
        )
        Base.metadata.drop_all(conn)
    engine.dispose()


def pytest_sessionstart(session):
    # forkserver 暖機只做 --collect-only，不連 DB，不需要 slot
    if session.config.option.collectonly:
        return

    conftest = sys.modules.get("tests.conftest")
    if conftest is None:
        raise RuntimeError("tests.conftest 尚未載入，無法套用 mutmut 隔離")

    slot = _acquire_slot()

    # fork 出來的 worker 會繼承父行程已改寫的 URL，因此以第一次看到的原值為準
    if not hasattr(conftest, "_mutmut_original_urls"):
        conftest._mutmut_original_urls = (
            conftest.TEST_DATABASE_URL,
            conftest.TEST_DATABASE_URL_SYNC,
        )
    base_url, base_sync_url = conftest._mutmut_original_urls

    slot_db = f"{urlsplit(base_url).path.lstrip('/')}_mm{slot}"
    _ensure_database(base_sync_url, slot_db)

    conftest.TEST_DATABASE_URL = _with_path(base_url, f"/{slot_db}")
    conftest.TEST_DATABASE_URL_SYNC = _with_path(base_sync_url, f"/{slot_db}")
    _drop_leftover_tables(conftest.TEST_DATABASE_URL_SYNC)

    from app.core.config import settings
    from app.services.redis_client import redis_client

    settings.REDIS_URL = _with_path(settings.REDIS_URL, f"/{slot + 1}")
    # fork 出來的 worker 會繼承父行程的連線池（綁定已關閉的 event loop），強制重建
    redis_client._pool = None


def pytest_sessionfinish(session, exitstatus):
    global _lock_fd
    if _lock_fd is not None:
        os.close(_lock_fd)
        _lock_fd = None
