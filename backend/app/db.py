"""로컬 SQLite 연결. 스레드마다 별도 연결을 쓰도록 호출마다 새로 연다."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
BUSY_TIMEOUT_SEC = 10


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_SEC)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(db_path: Path) -> Iterator[sqlite3.Connection]:
    """업무 로직 계층이 트랜잭션 경계를 잡을 때 쓴다 (BE-002). 정상 종료면 커밋, 예외면 롤백한다."""
    with connect(db_path) as conn:
        with conn:
            yield conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        # 여러 실행 스레드가 동시에 기록하므로 WAL로 읽기·쓰기 잠금 충돌을 줄인다.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
