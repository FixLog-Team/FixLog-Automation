"""실행 결과·시나리오 데이터 접근. 쿼리 실행과 결과 매핑만 한다 (BE-004).

트랜잭션은 열지 않는다. 호출하는 업무 로직(service.py)이 넘긴 연결을 쓴다 (BE-002).
"""
import json
import sqlite3
from datetime import datetime, timezone

MAX_LIST_LIMIT = 200

RUN_COLUMNS = (
    "id, batch_id, iteration, scenario_id, scenario_name, browser_type, headless, status, "
    "started_at, finished_at, duration_ms, failed_step, error_message, last_url, created_at"
)
STEP_COLUMNS = (
    "id, run_id, seq, step_id, step_name, status, started_at, finished_at, duration_ms, "
    "page_url, detail, error_message, screenshot_path"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---- batch -----------------------------------------------------------------
def insert_batch(conn: sqlite3.Connection, batch_id: str, scenario_id: str, options: dict,
                 status: str, created_at: str) -> None:
    conn.execute(
        "INSERT INTO batches (id, scenario_id, options_json, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (batch_id, scenario_id, json.dumps(options, ensure_ascii=False), status, created_at),
    )


def update_batch_finished(conn: sqlite3.Connection, batch_id: str, status: str, finished_at: str) -> None:
    conn.execute("UPDATE batches SET status = ?, finished_at = ? WHERE id = ?", (status, finished_at, batch_id))


def update_batches_status(conn: sqlite3.Connection, from_status: str, to_status: str, finished_at: str) -> None:
    conn.execute(
        "UPDATE batches SET status = ?, finished_at = ? WHERE status = ?", (to_status, finished_at, from_status)
    )


# ---- run -------------------------------------------------------------------
def insert_runs(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        "INSERT INTO runs (id, batch_id, iteration, scenario_id, scenario_name, browser_type, headless, "
        "status, created_at) VALUES (:id, :batch_id, :iteration, :scenario_id, :scenario_name, "
        ":browser_type, :headless, :status, :created_at)",
        rows,
    )


def update_run_started(conn: sqlite3.Connection, run_id: str, status: str, started_at: str) -> None:
    conn.execute("UPDATE runs SET status = ?, started_at = ? WHERE id = ?", (status, started_at, run_id))


def update_run_finished(conn: sqlite3.Connection, run_id: str, fields: dict) -> None:
    conn.execute(
        "UPDATE runs SET status = :status, finished_at = :finished_at, duration_ms = :duration_ms, "
        "failed_step = :failed_step, error_message = :error_message, last_url = :last_url WHERE id = :id",
        {**fields, "id": run_id},
    )


def update_runs_status(conn: sqlite3.Connection, from_statuses: tuple[str, ...], to_status: str,
                       message: str, finished_at: str) -> int:
    placeholders = ", ".join("?" for _ in from_statuses)
    cur = conn.execute(
        f"UPDATE runs SET status = ?, error_message = ?, finished_at = ? WHERE status IN ({placeholders})",
        (to_status, message, finished_at, *from_statuses),
    )
    return cur.rowcount


def select_run_list(conn: sqlite3.Connection, limit: int, offset: int,
                    status: str | None, scenario_id: str | None) -> dict:
    conditions, params = [], []
    if status:
        conditions.append("status = ?")
        params.append(status)
    if scenario_id:
        conditions.append("scenario_id = ?")
        params.append(scenario_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    total = conn.execute(f"SELECT COUNT(1) FROM runs {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {RUN_COLUMNS} FROM runs {where} ORDER BY created_at DESC, iteration DESC LIMIT ? OFFSET ?",
        [*params, min(limit, MAX_LIST_LIMIT), offset],
    ).fetchall()
    return {"total": total, "items": [dict(r) for r in rows]}


def select_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    row = conn.execute(f"SELECT {RUN_COLUMNS} FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def select_run_steps(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = conn.execute(f"SELECT {STEP_COLUMNS} FROM run_steps WHERE run_id = ? ORDER BY seq", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def select_run_totals(conn: sqlite3.Connection, passed: str, failed: str, in_progress: tuple[str, str]) -> dict:
    row = conn.execute(
        "SELECT COUNT(1) AS total, "
        "SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS passed, "
        "SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS failed, "
        "SUM(CASE WHEN status IN (?, ?) THEN 1 ELSE 0 END) AS in_progress, "
        "AVG(CASE WHEN status IN (?, ?) THEN duration_ms END) AS avg_duration_ms "
        "FROM runs",
        (passed, failed, *in_progress, passed, failed),
    ).fetchone()
    return dict(row)


def select_scenario_totals(conn: sqlite3.Connection, passed: str, failed: str) -> list[dict]:
    rows = conn.execute(
        "SELECT scenario_id, scenario_name, COUNT(1) AS total, "
        "SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS passed, "
        "SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS failed "
        "FROM runs GROUP BY scenario_id, scenario_name ORDER BY total DESC LIMIT 50",
        (passed, failed),
    ).fetchall()
    return [dict(r) for r in rows]


# ---- step ------------------------------------------------------------------
def insert_step(conn: sqlite3.Connection, step: dict) -> None:
    conn.execute(
        "INSERT INTO run_steps (run_id, seq, step_id, step_name, status, started_at, finished_at, "
        "duration_ms, page_url, detail, error_message, screenshot_path) VALUES (:run_id, :seq, :step_id, "
        ":step_name, :status, :started_at, :finished_at, :duration_ms, :page_url, :detail, :error_message, "
        ":screenshot_path)",
        step,
    )


# ---- custom scenario -------------------------------------------------------
def insert_custom_scenario(conn: sqlite3.Connection, scenario_id: str, name: str, description: str,
                           steps: list[str], created_at: str) -> None:
    conn.execute(
        "INSERT INTO custom_scenarios (id, name, description, steps_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (scenario_id, name, description, json.dumps(steps), created_at),
    )


def select_custom_scenario_list(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, description, steps_json, created_at FROM custom_scenarios ORDER BY created_at LIMIT ?",
        (MAX_LIST_LIMIT,),
    ).fetchall()
    return [{**dict(r), "steps": json.loads(r["steps_json"])} for r in rows]


def delete_custom_scenario(conn: sqlite3.Connection, scenario_id: str) -> int:
    return conn.execute("DELETE FROM custom_scenarios WHERE id = ?", (scenario_id,)).rowcount
