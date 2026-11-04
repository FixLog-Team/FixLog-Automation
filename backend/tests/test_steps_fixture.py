"""가짜 FixLog 화면(tests/fixture_site)에 실제 Chromium으로 시나리오를 실행해 단계·기록 동작을 검증한다."""
from app.automation.scenarios import BUILTIN_SCENARIOS, Scenario
from app.config import RunOptions
from app.constants import RunStatus, StepStatus
from app.runner import BatchRunner

SCENARIOS = {s.id: s for s in BUILTIN_SCENARIOS}


def _run(settings, records, scenario: Scenario, **options):
    runner = BatchRunner(settings, records)
    handle = runner.run_batch_blocking(
        scenario, RunOptions(scenario_id=scenario.id, step_delay_ms=0, timeout_sec=60, **options)
    )
    return records.get_run(handle.run_ids[0])


def _statuses(run):
    return {s["step_id"]: s["status"] for s in run["steps"]}


def test_full_scenario_passes_all_steps(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    run = _run(settings, records_for(settings), SCENARIOS["full"])

    assert run["status"] == RunStatus.PASSED, run
    assert all(s["status"] == StepStatus.PASSED for s in run["steps"]), run["steps"]
    by_id = {s["step_id"]: s for s in run["steps"]}
    created_url = by_id["verify_saved_document"]["page_url"]
    assert "/documents/new-" in created_url
    title = by_id["write_document"]["detail"].split("'")[1]
    assert title.startswith("자동화 테스트 문서 ")
    assert title in by_id["list_documents"]["detail"]
    assert "검색 결과 문서 1건" in by_id["verify_search_results"]["detail"]
    assert by_id["open_document"]["page_url"] == created_url
    assert "추천 태그" in by_id["ai_summary"]["detail"]
    assert "v2" in by_id["version_history"]["detail"]
    assert "작성한 문서 확인" in by_id["ai_search"]["detail"]
    assert by_id["delete_document"]["page_url"].endswith("/documents")
    assert "사라짐 확인" in by_id["delete_document"]["detail"]
    assert title in by_id["verify_trash"]["detail"]
    order = [s["step_id"] for s in run["steps"]]
    assert order.index("ai_search") < order.index("delete_document") < order.index("verify_trash")
    assert run["duration_ms"] > 0


def test_existing_document_journey(fixture_base_url, settings_factory, records_for):
    """문서를 만들지 않는 실행은 기존처럼 목록 첫 문서를 대상으로 쓴다."""
    settings = settings_factory(fixture_base_url)
    scenario = Scenario("t", "t", "", ("login", "list_documents", "search_input", "verify_search_results",
                                       "open_document", "close_browser"))
    run = _run(settings, records_for(settings), scenario)

    assert run["status"] == RunStatus.PASSED, run["steps"]
    by_id = {s["step_id"]: s for s in run["steps"]}
    assert "결제 오류 처리 가이드" in by_id["list_documents"]["detail"]
    assert by_id["open_document"]["page_url"].endswith("/documents/doc-1")


def test_write_scenario(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    run = _run(settings, records_for(settings), SCENARIOS["write"])

    assert run["status"] == RunStatus.PASSED, run["steps"]


def test_unsaved_document_fails_verification(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    scenario = Scenario("t", "t", "", ("login", "create_document", "write_document", "verify_saved_document",
                                       "close_browser"))
    run = _run(settings, records_for(settings), scenario)

    statuses = _statuses(run)
    assert statuses["write_document"] == StepStatus.PASSED
    assert statuses["verify_saved_document"] == StepStatus.FAILED
    assert run["failed_step"] == "저장 내용 확인"


def test_search_without_result_records_failure_and_screenshot(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    run = _run(settings, records_for(settings), SCENARIOS["search"], search_keyword="존재하지않는검색어")

    statuses = _statuses(run)
    assert statuses["verify_search_results"] == StepStatus.PASSED
    assert statuses["open_document"] == StepStatus.FAILED
    assert statuses["close_browser"] == StepStatus.PASSED
    assert run["status"] == RunStatus.FAILED
    assert run["failed_step"] == "문서 상세 진입"
    failed = next(s for s in run["steps"] if s["step_id"] == "open_document")
    assert "열 수 있는 문서가 없습니다" in failed["error_message"]
    assert (settings.screenshot_dir / failed["screenshot_path"]).exists()


def test_stop_on_failure_skips_all_following_steps(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    scenario = Scenario("t", "t", "", ("login", "ai_summary", "version_history", "close_browser"))
    run = _run(settings, records_for(settings), scenario, stop_on_failure=True)

    assert _statuses(run) == {
        "launch_browser": StepStatus.PASSED,
        "login": StepStatus.PASSED,
        "ai_summary": StepStatus.FAILED,
        "version_history": StepStatus.SKIPPED,
        "close_browser": StepStatus.PASSED,
    }


def test_login_fails_without_auth_state(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url, with_auth=False)
    run = _run(settings, records_for(settings), SCENARIOS["basic"])

    login_step = next(s for s in run["steps"] if s["step_id"] == "login")
    assert login_step["status"] == StepStatus.FAILED
    assert "python -m app.cli auth" in login_step["error_message"]
    assert login_step["screenshot_path"]


def test_ai_search_scenario(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    run = _run(settings, records_for(settings), SCENARIOS["ai_search"])

    assert run["status"] == RunStatus.PASSED, run["steps"]


def test_configured_document_title_is_used(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url, test_document_title="릴리스 체크리스트")
    run = _run(settings, records_for(settings), SCENARIOS["search"])

    assert run["status"] == RunStatus.PASSED, run["steps"]
    opened = next(s for s in run["steps"] if s["step_id"] == "open_document")
    assert opened["page_url"].endswith("/documents/doc-2")


def test_concurrent_runs(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    records = records_for(settings)
    handle = BatchRunner(settings, records).run_batch_blocking(
        SCENARIOS["basic"],
        RunOptions(scenario_id="basic", run_count=2, concurrency=2, step_delay_ms=0, interval_sec=2),
    )
    runs = [records.get_run(run_id) for run_id in handle.run_ids]
    assert [r["status"] for r in runs] == [RunStatus.PASSED, RunStatus.PASSED]
    assert records.get_stats()["passed"] == 2


def test_continue_after_failure_runs_following_steps(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    scenario = Scenario("t", "t", "", ("login", "ai_summary", "list_documents", "open_document",
                                       "version_history", "close_browser"))
    run = _run(settings, records_for(settings), scenario)

    assert _statuses(run) == {
        "launch_browser": StepStatus.PASSED,
        "login": StepStatus.PASSED,
        "ai_summary": StepStatus.FAILED,
        "list_documents": StepStatus.PASSED,
        "open_document": StepStatus.PASSED,
        "version_history": StepStatus.PASSED,
        "close_browser": StepStatus.PASSED,
    }
    assert run["status"] == RunStatus.FAILED
    assert run["failed_step"] == "AI 요약 실행"


def test_steps_requiring_failed_step_are_skipped(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url)
    # 문서 상세 화면이 아니어서 문서 작성이 실패한다.
    scenario = Scenario("t", "t", "", ("login", "write_document", "save_document", "verify_saved_document",
                                       "delete_document", "verify_trash", "list_documents", "close_browser"))
    run = _run(settings, records_for(settings), scenario)

    statuses = _statuses(run)
    assert statuses["write_document"] == StepStatus.FAILED
    for step_id in ("save_document", "verify_saved_document", "delete_document", "verify_trash"):
        assert statuses[step_id] == StepStatus.SKIPPED, step_id
    assert statuses["list_documents"] == StepStatus.PASSED
    by_id = {s["step_id"]: s for s in run["steps"]}
    assert by_id["save_document"]["detail"] == "'문서 작성' 실패로 실행하지 않음"
    assert by_id["verify_saved_document"]["detail"] == "'문서 저장' 실패로 실행하지 않음"
    assert by_id["verify_trash"]["detail"] == "'문서 삭제' 실패로 실행하지 않음"
