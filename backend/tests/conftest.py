import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.config import Settings
from app.db import init_db
from app.service import RunRecordService

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_site"


class SpaHandler(SimpleHTTPRequestHandler):
    """모든 경로에 index.html을 돌려주는 SPA 서버(Vercel rewrite와 같은 동작)."""

    def do_GET(self):
        self.path = "/index.html"
        return super().do_GET()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def fixture_base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SpaHandler, directory=str(FIXTURE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def make_settings(tmp_path: Path, base_url: str, *, with_auth: bool = True, **overrides) -> Settings:
    auth_path = tmp_path / ".auth" / "state.json"
    if with_auth:
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(json.dumps({
            "cookies": [],
            "origins": [{"origin": base_url, "localStorage": [{"name": "access_token", "value": "test-token"}]}],
        }), encoding="utf-8")
    values = dict(
        base_url=base_url,
        account_email="tester@example.com",
        account_password="not-a-real-password",
        browser_type="chromium",
        headless=True,
        auth_state_path=auth_path,
        data_dir=tmp_path / "data",
        test_document_title="",
        test_search_keyword="",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def settings_factory(tmp_path):
    def factory(base_url: str = "http://127.0.0.1:9", **kwargs) -> Settings:
        settings = make_settings(tmp_path, base_url, **kwargs)
        init_db(settings.db_path)
        return settings
    return factory


@pytest.fixture
def records_for():
    return lambda settings: RunRecordService(settings.db_path)
