"""일반 브라우저에서 복사한 토큰으로 인증 상태를 만드는 auth-import 동작을 검증한다."""
import json

import pytest

from app.automation.auth import AuthError, build_imported_auth_state, save_imported_auth
from app.automation.scenarios import Scenario
from app.config import RunOptions
from app.constants import RunStatus
from app.runner import BatchRunner


def test_imported_state_keeps_only_fixlog_keys():
    pasted = json.dumps({"access_token": "a", "refresh_token": "r", "workspace_id": None})
    state = build_imported_auth_state("https://example.test", pasted)
    assert state == {"cookies": [], "origins": [{
        "origin": "https://example.test",
        "localStorage": [{"name": "access_token", "value": "a"}, {"name": "refresh_token", "value": "r"}],
    }]}


@pytest.mark.parametrize("pasted", [
    "not json",
    "[]",
    json.dumps({"access_token": ""}),
    json.dumps({"access_token": None}),
    json.dumps({"access_token": "a", "other": "x"}),
    json.dumps({"access_token": "a", "refresh_token": 1}),
])
def test_imported_state_rejects_bad_input(pasted):
    with pytest.raises(AuthError):
        build_imported_auth_state("https://example.test", pasted)


def test_imported_error_message_does_not_contain_token():
    with pytest.raises(AuthError) as error:
        build_imported_auth_state("https://example.test", json.dumps({"access_token": "secret-x", "bad": "y"}))
    assert "secret-x" not in str(error.value)


def test_imported_state_passes_login_step(fixture_base_url, settings_factory, records_for):
    settings = settings_factory(fixture_base_url, with_auth=False)
    save_imported_auth(settings, json.dumps({"access_token": "test-token"}))

    records = records_for(settings)
    scenario = Scenario("t", "t", "", ("login", "close_browser"))
    handle = BatchRunner(settings, records).run_batch_blocking(
        scenario, RunOptions(scenario_id=scenario.id, step_delay_ms=0, timeout_sec=60)
    )
    run = records.get_run(handle.run_ids[0])
    assert run["status"] == RunStatus.PASSED, run["steps"]
