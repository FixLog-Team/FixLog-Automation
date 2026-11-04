"""명령줄 진입점.

  python -m app.cli auth                 테스트 계정으로 1회 로그인하고 인증 상태 저장
  python -m app.cli scenarios            시나리오 목록
  python -m app.cli run --scenario basic 시나리오 실행 후 결과 출력
  python -m app.cli serve                API + 대시보드 서버 실행
"""
import argparse
import asyncio
import logging
import sys

from pydantic import ValidationError

from .automation.auth import AuthError, bootstrap_auth
from .automation.scenarios import find_scenario, list_scenarios
from .config import (
    DEFAULT_CONCURRENCY, DEFAULT_INTERVAL_SEC, DEFAULT_RUN_COUNT, DEFAULT_RUN_TIMEOUT_SEC, DEFAULT_STEP_DELAY_MS,
    RunOptions, load_settings,
)
from .constants import RunStatus
from .db import init_db
from .service import RunRecordService
from .runner import BatchRunner, new_playwright_event_loop

logger = logging.getLogger("app.cli")

DEFAULT_AUTH_WAIT_SEC = 300
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Windows 콘솔(cp949)에서도 한글·기호가 깨지지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _command_auth(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.account_email:
        logger.info("TEST_ACCOUNT_EMAIL이 없어 Google 화면에서 직접 입력해야 합니다.")
    try:
        with asyncio.Runner(loop_factory=new_playwright_event_loop) as runner:
            runner.run(bootstrap_auth(settings, args.wait))
    except AuthError as error:
        logger.error("로그인 실패: %s", error)
        return 1
    return 0


def _command_scenarios(_: argparse.Namespace) -> int:
    settings = load_settings()
    init_db(settings.db_path)
    for scenario in list_scenarios(RunRecordService(settings.db_path)):
        sys.stdout.write(f"{scenario.id:12} {scenario.name} - {' > '.join(scenario.steps)}\n")
    return 0


def _command_run(args: argparse.Namespace) -> int:
    settings = load_settings()
    init_db(settings.db_path)
    records = RunRecordService(settings.db_path)
    scenario = find_scenario(records, args.scenario)
    if scenario is None:
        logger.error("시나리오를 찾을 수 없습니다: %s (python -m app.cli scenarios 로 확인)", args.scenario)
        return 2
    try:
        options = RunOptions(
            scenario_id=scenario.id,
            browser_type=args.browser,
            headless=args.headless,
            run_count=args.count,
            concurrency=args.concurrency,
            step_delay_ms=args.delay_ms,
            interval_sec=args.interval,
            timeout_sec=args.timeout,
            save_success_screenshots=args.screenshots,
            search_keyword=args.keyword,
            stop_on_failure=args.stop_on_failure,
        )
    except ValidationError as error:
        logger.error("실행 설정 오류:\n%s", error)
        return 2

    handle = BatchRunner(settings, records).run_batch_blocking(scenario, options)
    has_failure = False
    for run_id in handle.run_ids:
        run = records.get_run(run_id)
        has_failure = has_failure or run["status"] != RunStatus.PASSED
        sys.stdout.write(f"\n[{run['iteration']}] {run['status']}  {run['duration_ms']}ms  run_id={run_id}\n")
        for step in run["steps"]:
            line = f"  {step['seq']:>2}. {step['status']:<7} {step['step_name']}"
            if step["duration_ms"] is not None:
                line += f" ({step['duration_ms']}ms)"
            if step["detail"]:
                line += f" - {step['detail']}"
            if step["error_message"]:
                line += f"\n      오류: {step['error_message'].splitlines()[0]}"
            if step["screenshot_path"]:
                line += f"\n      스크린샷: {settings.screenshot_dir / step['screenshot_path']}"
            sys.stdout.write(line + "\n")
    return 1 if has_failure else 0


def _command_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .main import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="FixLog 브라우저 자동화")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="테스트 계정 Google 로그인 후 인증 상태 저장")
    auth.add_argument("--wait", type=int, default=DEFAULT_AUTH_WAIT_SEC, help="사람이 로그인을 마칠 때까지 기다릴 초")
    auth.set_defaults(func=_command_auth)

    scenarios = sub.add_parser("scenarios", help="시나리오 목록")
    scenarios.set_defaults(func=_command_scenarios)

    run = sub.add_parser("run", help="시나리오 실행")
    run.add_argument("--scenario", required=True)
    run.add_argument("--count", type=int, default=DEFAULT_RUN_COUNT, help="실행 횟수")
    run.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="동시 실행 수")
    run.add_argument("--delay-ms", type=int, default=DEFAULT_STEP_DELAY_MS, help="단계 사이 대기(ms)")
    run.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SEC, help="실행 간격(초)")
    run.add_argument("--timeout", type=int, default=DEFAULT_RUN_TIMEOUT_SEC, help="1회 실행 시간 제한(초)")
    run.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default=None)
    run.add_argument("--stop-on-failure", action="store_true",
                     help="첫 실패에서 멈춤(기본: 실패를 기록하고 다음 단계 계속)")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--headless", dest="headless", action="store_true", default=None)
    mode.add_argument("--headed", dest="headless", action="store_false")
    run.add_argument("--keyword", default=None, help="검색어(없으면 TEST_SEARCH_KEYWORD 또는 대상 문서 제목)")
    run.add_argument("--screenshots", action="store_true", help="성공한 단계도 스크린샷 저장")
    run.set_defaults(func=_command_run)

    serve = sub.add_parser("serve", help="API·대시보드 서버 실행")
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.set_defaults(func=_command_serve)
    return parser


def main() -> int:
    _configure_logging()
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
