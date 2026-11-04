"""실행 기록 업무 로직. 트랜잭션 경계를 여기서 잡는다 (BE-002, BE-003)."""
from pathlib import Path

from . import repository as repo
from .constants import IN_PROGRESS_RUN_STATUSES, RunStatus
from .db import connect, transaction
from .repository import now_iso


class RunRecordService:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ---- 기록(실행기에서 호출) ----------------------------------------------
    def create_batch(self, batch_id: str, scenario_id: str, options: dict, run_rows: list[dict]) -> None:
        """실행 요청과 회차별 실행 행을 함께 저장한다. 하나라도 실패하면 모두 저장하지 않는다."""
        with transaction(self.db_path) as conn:
            repo.insert_batch(conn, batch_id, scenario_id, options, RunStatus.RUNNING, now_iso())
            repo.insert_runs(conn, run_rows)

    def finish_batch(self, batch_id: str, status: str) -> None:
        with transaction(self.db_path) as conn:
            repo.update_batch_finished(conn, batch_id, status, now_iso())

    def start_run(self, run_id: str, started_at: str) -> None:
        with transaction(self.db_path) as conn:
            repo.update_run_started(conn, run_id, RunStatus.RUNNING, started_at)

    def finish_run(self, run_id: str, fields: dict) -> None:
        with transaction(self.db_path) as conn:
            repo.update_run_finished(conn, run_id, fields)

    def record_step(self, step: dict) -> None:
        with transaction(self.db_path) as conn:
            repo.insert_step(conn, step)

    def fail_unfinished_runs(self, message: str) -> int:
        """서버 중단 등으로 대기·실행 중 상태로 남은 실행과 실행 요청을 실패로 정리한다."""
        finished_at = now_iso()
        with transaction(self.db_path) as conn:
            count = repo.update_runs_status(conn, IN_PROGRESS_RUN_STATUSES, RunStatus.FAILED, message, finished_at)
            repo.update_batches_status(conn, RunStatus.RUNNING, RunStatus.FAILED, finished_at)
        return count

    # ---- 조회 ----------------------------------------------------------------
    def get_run_list(self, limit: int, offset: int, status: str | None, scenario_id: str | None) -> dict:
        with connect(self.db_path) as conn:
            return repo.select_run_list(conn, limit, offset, status, scenario_id)

    def get_run(self, run_id: str) -> dict | None:
        with connect(self.db_path) as conn:
            run = repo.select_run(conn, run_id)
            if run is None:
                return None
            return {**run, "steps": repo.select_run_steps(conn, run_id)}

    def get_stats(self) -> dict:
        with connect(self.db_path) as conn:
            totals = repo.select_run_totals(conn, RunStatus.PASSED, RunStatus.FAILED, IN_PROGRESS_RUN_STATUSES)
            by_scenario = repo.select_scenario_totals(conn, RunStatus.PASSED, RunStatus.FAILED)
        avg = totals["avg_duration_ms"]
        return {
            "total": totals["total"] or 0,
            "passed": totals["passed"] or 0,
            "failed": totals["failed"] or 0,
            "in_progress": totals["in_progress"] or 0,
            "avg_duration_ms": round(avg) if avg else None,
            "by_scenario": by_scenario,
        }

    # ---- 사용자 정의 시나리오 -------------------------------------------------
    def get_custom_scenario_list(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return repo.select_custom_scenario_list(conn)

    def add_custom_scenario(self, scenario_id: str, name: str, description: str, steps: list[str]) -> None:
        with transaction(self.db_path) as conn:
            repo.insert_custom_scenario(conn, scenario_id, name, description, steps, now_iso())

    def remove_custom_scenario(self, scenario_id: str) -> bool:
        with transaction(self.db_path) as conn:
            return repo.delete_custom_scenario(conn, scenario_id) > 0
