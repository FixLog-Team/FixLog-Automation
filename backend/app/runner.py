"""시나리오 실행기.

실행 요청(batch) 하나를 별도 스레드의 이벤트 루프에서 돌린다. FastAPI 이벤트 루프와 분리해
Windows에서도 Playwright가 요구하는 Proactor 루프를 확실히 쓰기 위해서다.
"""
import asyncio
import logging
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Playwright, async_playwright

from .automation.browser import launch_browser, new_context
from .automation.scenarios import Scenario
from .automation.steps import CLOSE_BROWSER_STEP_ID, STEP_REGISTRY, StepContext, StepDefinition, StepFailure
from .config import RunOptions, Settings
from .constants import RunStatus, StepStatus
from .repository import now_iso
from .service import RunRecordService

logger = logging.getLogger(__name__)

LAUNCH_STEP_ID = "launch_browser"
LAUNCH_STEP_NAME = "브라우저 실행"
ERROR_TEXT_LIMIT = 2_000
SKIP_AFTER_FAILURE = "앞 단계 실패로 실행하지 않음"


class BatchAlreadyRunningError(RuntimeError):
    """동시 실행 상한을 지키기 위해 실행 요청은 한 번에 하나만 받는다."""


@dataclass(frozen=True)
class BatchHandle:
    batch_id: str
    run_ids: list[str]


@dataclass
class StepOutcome:
    status: str
    error_message: str | None = None
    timed_out: bool = False


def new_playwright_event_loop() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()


def _summarize_error(error: BaseException) -> str:
    message = str(error).strip() or error.__class__.__name__
    return message[:ERROR_TEXT_LIMIT]


class BatchRunner:
    def __init__(self, settings: Settings, records: RunRecordService):
        self.settings = settings
        self.records = records
        self._lock = threading.Lock()
        self._active_batch_id: str | None = None

    @property
    def active_batch_id(self) -> str | None:
        return self._active_batch_id

    # ---- 진입점 --------------------------------------------------------------
    def start_batch(self, scenario: Scenario, options: RunOptions) -> BatchHandle:
        """백그라운드 스레드에서 실행하고 바로 돌아온다(API용)."""
        handle = self._prepare_batch(scenario, options)
        thread = threading.Thread(
            target=self._run_batch_in_thread, args=(handle, scenario, options), daemon=True,
            name=f"batch-{handle.batch_id[:8]}",
        )
        thread.start()
        return handle

    def run_batch_blocking(self, scenario: Scenario, options: RunOptions) -> BatchHandle:
        """끝날 때까지 기다린다(CLI용)."""
        handle = self._prepare_batch(scenario, options)
        self._run_batch_in_thread(handle, scenario, options)
        return handle

    # ---- batch ---------------------------------------------------------------
    def _prepare_batch(self, scenario: Scenario, options: RunOptions) -> BatchHandle:
        with self._lock:
            if self._active_batch_id is not None:
                raise BatchAlreadyRunningError(f"이미 실행 중인 요청이 있습니다: {self._active_batch_id}")
            batch_id = uuid.uuid4().hex
            self._active_batch_id = batch_id

        browser_type = options.resolved_browser(self.settings)
        headless = options.resolved_headless(self.settings)
        created_at = now_iso()
        run_rows = [
            {
                "id": uuid.uuid4().hex,
                "batch_id": batch_id,
                "iteration": index + 1,
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
                "browser_type": browser_type,
                "headless": int(headless),
                "status": RunStatus.QUEUED,
                "created_at": created_at,
            }
            for index in range(options.run_count)
        ]
        try:
            self.records.create_batch(batch_id, scenario.id, options.model_dump(), run_rows)
        except Exception:
            self._release(batch_id)
            raise
        return BatchHandle(batch_id, [row["id"] for row in run_rows])

    def _release(self, batch_id: str) -> None:
        with self._lock:
            if self._active_batch_id == batch_id:
                self._active_batch_id = None

    def _run_batch_in_thread(self, handle: BatchHandle, scenario: Scenario, options: RunOptions) -> None:
        status = RunStatus.FAILED
        try:
            with asyncio.Runner(loop_factory=new_playwright_event_loop) as runner:
                statuses = runner.run(self._run_batch(handle, scenario, options))
            status = RunStatus.PASSED if all(s == RunStatus.PASSED for s in statuses) else RunStatus.FAILED
        except Exception:  # 백그라운드 스레드의 최상위 처리기: 남은 실행을 실패로 정리한다 (COM-031 예외)
            logger.exception("batch %s 실행 중 예상하지 못한 오류", handle.batch_id)
            self.records.fail_unfinished_runs("실행기 내부 오류로 중단되었습니다. 서버 로그를 확인하세요.")
        finally:
            self.records.finish_batch(handle.batch_id, status)
            self._release(handle.batch_id)

    async def _run_batch(self, handle: BatchHandle, scenario: Scenario, options: RunOptions) -> list[str]:
        semaphore = asyncio.Semaphore(options.concurrency)
        async with async_playwright() as playwright:
            tasks = []
            for index, run_id in enumerate(handle.run_ids):
                if index > 0:
                    # 실행 간격: 다음 실행의 시작을 최소 interval_sec만큼 늦춰 요청 빈도를 제한한다.
                    await asyncio.sleep(options.interval_sec)
                await semaphore.acquire()
                tasks.append(asyncio.create_task(
                    self._run_one_and_release(playwright, semaphore, run_id, scenario, options)
                ))
            return list(await asyncio.gather(*tasks))

    async def _run_one_and_release(self, playwright: Playwright, semaphore: asyncio.Semaphore,
                                   run_id: str, scenario: Scenario, options: RunOptions) -> str:
        try:
            return await self._run_one(playwright, run_id, scenario, options)
        finally:
            semaphore.release()

    # ---- run -----------------------------------------------------------------
    async def _run_one(self, playwright: Playwright, run_id: str, scenario: Scenario, options: RunOptions) -> str:
        started_at = now_iso()
        started = time.monotonic()
        deadline = started + options.timeout_sec
        self.records.start_run(run_id, started_at)
        logger.info("run %s 시작: 시나리오=%s", run_id, scenario.id)

        ctx = StepContext(
            base_url=self.settings.base_url,
            has_auth_state=self.settings.auth_state_path.exists(),
            configured_document_title=self.settings.test_document_title,
            configured_search_keyword=options.search_keyword or self.settings.test_search_keyword,
        )
        failed_step: str | None = None
        error_message: str | None = None
        last_url: str | None = None
        # 이 실행에서 끝난 단계의 결과. 선행 단계 실패 여부를 판단한다.
        step_results: dict[str, str] = {}
        # 브라우저 실행 실패·시간 초과는 계속할 수 없어 뒤 단계를 모두 건너뛴다.
        halt_reason: str | None = None
        try:
            outcome = await self._launch(playwright, ctx, run_id, options)
            if outcome.status == StepStatus.FAILED:
                failed_step, error_message = LAUNCH_STEP_NAME, outcome.error_message
                halt_reason = f"'{LAUNCH_STEP_NAME}' 실패로 실행하지 않음"

            for seq, step_id in enumerate(scenario.steps, start=1):
                step = STEP_REGISTRY[step_id]
                skip_reason = self._skip_reason(step, step_results, failed_step, halt_reason, options)
                if skip_reason is not None:
                    self._record_skipped(run_id, seq, step, skip_reason)
                    step_results[step.id] = StepStatus.SKIPPED
                    continue
                if ctx.page is not None and not ctx.page.is_closed():
                    last_url = ctx.page.url
                outcome = await self._execute_step(ctx, run_id, seq, step, deadline, options)
                step_results[step.id] = outcome.status
                if outcome.status == StepStatus.FAILED and failed_step is None:
                    failed_step, error_message = step.name, outcome.error_message
                if outcome.timed_out:
                    halt_reason = f"실행 시간 제한({options.timeout_sec}초) 초과로 실행하지 않음"
                is_last = seq == len(scenario.steps)
                if outcome.status == StepStatus.PASSED and not is_last and options.step_delay_ms > 0:
                    # 사용자가 설정한 "단계 사이 대기"(사람과 비슷한 속도). 화면 대기 용도가 아니다.
                    await asyncio.sleep(options.step_delay_ms / 1000)
        finally:
            await self._close_quietly(ctx)

        status = RunStatus.FAILED if failed_step else RunStatus.PASSED
        self.records.finish_run(run_id, {
            "status": status,
            "finished_at": now_iso(),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "failed_step": failed_step,
            "error_message": error_message,
            "last_url": last_url,
        })
        logger.info("run %s 종료: %s%s", run_id, status, f" (실패 단계: {failed_step})" if failed_step else "")
        return status

    @staticmethod
    def _skip_reason(step: StepDefinition, step_results: dict[str, str], failed_step: str | None,
                     halt_reason: str | None, options: RunOptions) -> str | None:
        """이 단계를 건너뛸 이유. 실행해야 하면 None. 브라우저 종료는 항상 실행한다."""
        if step.id == CLOSE_BROWSER_STEP_ID:
            return None
        if halt_reason is not None:
            return halt_reason
        if options.stop_on_failure and failed_step is not None:
            return SKIP_AFTER_FAILURE
        for required_id in step.requires:
            if step_results.get(required_id) in (StepStatus.FAILED, StepStatus.SKIPPED):
                return f"'{STEP_REGISTRY[required_id].name}' 실패로 실행하지 않음"
        return None

    async def _launch(self, playwright: Playwright, ctx: StepContext, run_id: str, options: RunOptions) -> StepOutcome:
        started_at = now_iso()
        started = time.monotonic()
        browser_type = options.resolved_browser(self.settings)
        headless = options.resolved_headless(self.settings)
        outcome = StepOutcome(StepStatus.PASSED)
        try:
            ctx.browser = await launch_browser(playwright, browser_type, headless)
            ctx.context = await new_context(ctx.browser, self.settings.auth_state_path)
            ctx.page = await ctx.context.new_page()
        except PlaywrightError as error:
            logger.warning("run %s 브라우저 실행 실패", run_id, exc_info=error)
            outcome = StepOutcome(StepStatus.FAILED, _summarize_error(error))
        auth_note = "저장된 인증 상태 사용" if ctx.has_auth_state else "저장된 인증 상태 없음"
        self.records.record_step({
            "run_id": run_id, "seq": 0, "step_id": LAUNCH_STEP_ID, "step_name": LAUNCH_STEP_NAME,
            "status": outcome.status, "started_at": started_at, "finished_at": now_iso(),
            "duration_ms": int((time.monotonic() - started) * 1000), "page_url": None,
            "detail": f"{browser_type} ({'headless' if headless else 'headed'}), {auth_note}",
            "error_message": outcome.error_message, "screenshot_path": None,
        })
        return outcome

    async def _execute_step(self, ctx: StepContext, run_id: str, seq: int, step: StepDefinition,
                            deadline: float, options: RunOptions) -> StepOutcome:
        started_at = now_iso()
        started = time.monotonic()
        detail: str | None = None
        outcome = StepOutcome(StepStatus.PASSED)
        remaining = deadline - started
        try:
            if remaining <= 0 and step.id != CLOSE_BROWSER_STEP_ID:
                raise TimeoutError
            async with asyncio.timeout(max(remaining, 5) if step.id == CLOSE_BROWSER_STEP_ID else remaining):
                detail = await step.func(ctx)
        except StepFailure as error:
            outcome = StepOutcome(StepStatus.FAILED, str(error))
        except TimeoutError:
            outcome = StepOutcome(StepStatus.FAILED, f"실행 시간 제한({options.timeout_sec}초)을 넘었습니다.",
                                  timed_out=True)
        except AssertionError as error:  # Playwright expect() 실패
            outcome = StepOutcome(StepStatus.FAILED, _summarize_error(error))
        except PlaywrightError as error:
            outcome = StepOutcome(StepStatus.FAILED, _summarize_error(error))

        page_url = ctx.page.url if ctx.page is not None and not ctx.page.is_closed() else None
        is_failed = outcome.status == StepStatus.FAILED
        screenshot_path = None
        if is_failed or options.save_success_screenshots:
            screenshot_path = await self._take_screenshot(ctx, run_id, seq, step.id)
        if is_failed:
            logger.warning("run %s 단계 실패 [%s] %s", run_id, step.id, (outcome.error_message or "").splitlines()[0])

        self.records.record_step({
            "run_id": run_id, "seq": seq, "step_id": step.id, "step_name": step.name,
            "status": outcome.status, "started_at": started_at, "finished_at": now_iso(),
            "duration_ms": int((time.monotonic() - started) * 1000), "page_url": page_url,
            "detail": detail, "error_message": outcome.error_message, "screenshot_path": screenshot_path,
        })
        return outcome

    def _record_skipped(self, run_id: str, seq: int, step: StepDefinition, reason: str) -> None:
        self.records.record_step({
            "run_id": run_id, "seq": seq, "step_id": step.id, "step_name": step.name,
            "status": StepStatus.SKIPPED, "started_at": None, "finished_at": None, "duration_ms": None,
            "page_url": None, "detail": reason, "error_message": None,
            "screenshot_path": None,
        })

    async def _take_screenshot(self, ctx: StepContext, run_id: str, seq: int, step_id: str) -> str | None:
        if ctx.page is None or ctx.page.is_closed():
            return None
        relative = Path(run_id) / f"{seq:02d}_{step_id}.png"
        target = self.settings.screenshot_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            await ctx.page.screenshot(path=str(target), full_page=True)
        except PlaywrightError as error:
            logger.warning("run %s 스크린샷 저장 실패", run_id, exc_info=error)
            return None
        return relative.as_posix()

    async def _close_quietly(self, ctx: StepContext) -> None:
        """시나리오에 브라우저 종료 단계가 없거나 실패해도 브라우저는 반드시 닫는다 (COM-034)."""
        for closable in (ctx.context, ctx.browser):
            if closable is None:
                continue
            try:
                await closable.close()
            except PlaywrightError as error:
                logger.debug("브라우저 정리 중 오류(무시)", exc_info=error)
        ctx.page = ctx.context = ctx.browser = None
