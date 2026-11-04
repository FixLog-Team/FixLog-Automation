from fastapi.testclient import TestClient

from app.main import create_app
from app.runner import BatchHandle


class FakeRunner:
    """API 계층 검증용. 실제 브라우저를 띄우지 않는다."""

    active_batch_id = None

    def __init__(self):
        self.started = []

    def start_batch(self, scenario, options):
        self.started.append((scenario.id, options))
        return BatchHandle("batch-1", ["run-1"])


def _client(settings, runner=None):
    return TestClient(create_app(settings, runner or FakeRunner()))


def test_run_request_over_limit_is_rejected(settings_factory):
    client = _client(settings_factory())
    response = client.post("/api/runs", json={"scenario_id": "basic", "concurrency": 5, "run_count": 30})
    assert response.status_code == 422
    fields = {err["loc"][-1] for err in response.json()["detail"]}
    assert fields == {"concurrency", "run_count"}


def test_run_request_unknown_scenario(settings_factory):
    response = _client(settings_factory()).post("/api/runs", json={"scenario_id": "nope"})
    assert response.status_code == 404


def test_run_request_accepted(settings_factory):
    runner = FakeRunner()
    response = _client(settings_factory(), runner).post("/api/runs", json={"scenario_id": "search", "run_count": 3})
    assert response.status_code == 202
    assert runner.started[0][0] == "search"
    assert runner.started[0][1].run_count == 3


def test_config_does_not_expose_password(settings_factory):
    body = _client(settings_factory()).get("/api/config").json()
    assert "not-a-real-password" not in str(body)
    assert body["has_password"] is True
    assert body["account_email"] == "te***@example.com"
    assert body["limits"]["max_concurrency"] == 3


def test_custom_scenario_lifecycle(settings_factory):
    client = _client(settings_factory())
    bad = client.post("/api/scenarios", json={"name": "x", "steps": ["login", "hack"]})
    assert bad.status_code == 422

    created = client.post("/api/scenarios", json={"name": "로그인만", "steps": ["login", "close_browser"]})
    assert created.status_code == 201
    scenario_id = created.json()["id"]
    ids = [s["id"] for s in client.get("/api/scenarios").json()]
    assert "basic" in ids and scenario_id in ids

    assert client.delete("/api/scenarios/basic").status_code == 400
    assert client.delete(f"/api/scenarios/{scenario_id}").status_code == 204
    assert client.delete(f"/api/scenarios/{scenario_id}").status_code == 404


def test_runs_and_stats_empty(settings_factory):
    client = _client(settings_factory())
    assert client.get("/api/runs").json() == {"total": 0, "items": []}
    assert client.get("/api/stats").json()["total"] == 0
    assert client.get("/api/runs/unknown").status_code == 404


def test_screenshot_path_traversal_blocked(settings_factory):
    client = _client(settings_factory())
    for path in ("/screenshots/../fixlog_automation.db", "/screenshots/..%2Ffixlog_automation.db"):
        response = client.get(path)
        # 대시보드 빌드가 있으면 index.html(200)이 올 수 있다. DB 파일 내용만 나오지 않으면 된다.
        assert b"SQLite format" not in response.content


def test_unknown_api_path_is_404_not_dashboard(settings_factory, monkeypatch, tmp_path):
    from app import main
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
    monkeypatch.setattr(main, "FRONTEND_DIST", dist)
    client = _client(settings_factory())
    assert client.get("/api/nope").status_code == 404
    deep_link = client.get("/runs/abc")
    assert deep_link.status_code == 200 and "dashboard" in deep_link.text
