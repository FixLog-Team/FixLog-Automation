"""FastAPI 앱. 요청 값 검증과 서비스 호출, 응답 변환만 한다 (BE-001)."""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .automation.scenarios import (
    ScenarioError, create_custom_scenario, delete_custom_scenario, find_scenario, list_scenarios,
)
from .automation.steps import STEP_DEFINITIONS
from .config import PROJECT_ROOT, RunOptions, Settings, limits, load_settings
from .db import init_db
from .runner import BatchAlreadyRunningError, BatchRunner
from .service import RunRecordService

logger = logging.getLogger(__name__)

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


class SpaStaticFiles(StaticFiles):
    """빌드된 React 대시보드를 제공한다. 없는 경로는 index.html로 돌려 화면 라우터가 처리하게 한다."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            # path는 OS 경로 구분자로 바뀌어 들어오므로(Windows는 \) 요청 URL로 API 여부를 판단한다.
            if error.status_code != 404 or scope["path"].startswith("/api/"):
                raise
            return await super().get_response("index.html", scope)


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field("", max_length=300)
    steps: list[str] = Field(min_length=1, max_length=30)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


def create_app(settings: Settings | None = None, runner: BatchRunner | None = None) -> FastAPI:
    settings = settings or load_settings()
    init_db(settings.db_path)
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    records = RunRecordService(settings.db_path)
    runner = runner or BatchRunner(settings, records)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        cleaned = records.fail_unfinished_runs("서버가 재시작되어 실행이 중단되었습니다.")
        if cleaned:
            logger.info("중단된 실행 %s건을 실패로 정리했습니다.", cleaned)
        yield

    app = FastAPI(title="FixLog Automation", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/config")
    def get_config() -> dict:
        auth_path = settings.auth_state_path
        auth_updated_at = None
        if auth_path.exists():
            auth_updated_at = datetime.fromtimestamp(auth_path.stat().st_mtime, timezone.utc).isoformat()
        return {
            "base_url": settings.base_url,
            "browser_type": settings.browser_type,
            "headless": settings.headless,
            "account_email": _mask_email(settings.account_email),
            "has_password": bool(settings.account_password),
            "has_auth_state": auth_path.exists(),
            "auth_state_updated_at": auth_updated_at,
            "test_document_title": settings.test_document_title,
            "test_search_keyword": settings.test_search_keyword,
            "active_batch_id": runner.active_batch_id,
            "limits": limits(),
        }

    @app.get("/api/steps")
    def get_steps() -> list[dict]:
        return [{"id": s.id, "name": s.name, "description": s.description} for s in STEP_DEFINITIONS]

    @app.get("/api/scenarios")
    def get_scenarios() -> list[dict]:
        return [s.to_dict() for s in list_scenarios(records)]

    @app.post("/api/scenarios", status_code=201)
    def post_scenario(body: ScenarioCreate) -> dict:
        try:
            return create_custom_scenario(records, body.name, body.description, body.steps).to_dict()
        except ScenarioError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.delete("/api/scenarios/{scenario_id}", status_code=204)
    def remove_scenario(scenario_id: str) -> None:
        try:
            is_deleted = delete_custom_scenario(records, scenario_id)
        except ScenarioError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if not is_deleted:
            raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다.")

    @app.post("/api/runs", status_code=202)
    def post_run(options: RunOptions) -> dict:
        scenario = find_scenario(records, options.scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail=f"시나리오를 찾을 수 없습니다: {options.scenario_id}")
        try:
            handle = runner.start_batch(scenario, options)
        except BatchAlreadyRunningError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"batch_id": handle.batch_id, "run_ids": handle.run_ids}

    @app.get("/api/runs")
    def get_runs(
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(0, ge=0),
        status: str | None = Query(None, max_length=20),
        scenario_id: str | None = Query(None, max_length=64),
    ) -> dict:
        return records.get_run_list(limit, offset, status, scenario_id)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        run = records.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="실행을 찾을 수 없습니다.")
        return run

    @app.get("/api/stats")
    def get_stats() -> dict:
        return records.get_stats()

    app.mount("/screenshots", StaticFiles(directory=settings.screenshot_dir), name="screenshots")
    if FRONTEND_DIST.exists():
        app.mount("/", SpaStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app
