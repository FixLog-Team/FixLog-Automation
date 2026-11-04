"""환경변수와 실행 설정.

환경마다 다른 값(접속 주소, 계정, 경로)은 모두 여기서 환경변수로 읽는다 (COM-006).
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

BrowserType = Literal["chromium", "firefox", "webkit"]

DEFAULT_BASE_URL = "https://fix-log-front-theta.vercel.app"
DEFAULT_BROWSER_TYPE: BrowserType = "chromium"
DEFAULT_AUTH_STATE_PATH = BACKEND_DIR / ".auth" / "state.json"
DEFAULT_DATA_DIR = BACKEND_DIR / "data"

# 실제 서비스에 붙는 자동화이므로 부하·분석 데이터 오염을 막기 위해 상한을 둔다.
MAX_RUN_COUNT = 20
MAX_CONCURRENCY = 3
MIN_INTERVAL_SEC = 2.0
MAX_INTERVAL_SEC = 600.0
MAX_STEP_DELAY_MS = 5_000
MIN_RUN_TIMEOUT_SEC = 10
MAX_RUN_TIMEOUT_SEC = 600

DEFAULT_RUN_COUNT = 1
DEFAULT_CONCURRENCY = 1
DEFAULT_STEP_DELAY_MS = 500
DEFAULT_INTERVAL_SEC = 3.0
DEFAULT_RUN_TIMEOUT_SEC = 180

TRUE_VALUES = {"1", "true", "yes", "on"}


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in TRUE_VALUES


def _read_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else (PROJECT_ROOT / path)


@dataclass(frozen=True)
class Settings:
    base_url: str
    account_email: str
    account_password: str
    browser_type: BrowserType
    headless: bool
    auth_state_path: Path
    data_dir: Path
    test_document_title: str
    test_search_keyword: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "fixlog_automation.db"

    @property
    def screenshot_dir(self) -> Path:
        return self.data_dir / "screenshots"


def load_settings() -> Settings:
    browser_type = os.getenv("BROWSER_TYPE", DEFAULT_BROWSER_TYPE).strip().lower()
    if browser_type not in ("chromium", "firefox", "webkit"):
        raise ValueError(f"BROWSER_TYPE은 chromium, firefox, webkit 중 하나여야 합니다: {browser_type}")
    return Settings(
        base_url=os.getenv("FIXLOG_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/"),
        account_email=os.getenv("TEST_ACCOUNT_EMAIL", "").strip(),
        account_password=os.getenv("TEST_ACCOUNT_PASSWORD", ""),
        browser_type=browser_type,  # type: ignore[arg-type]
        headless=_read_bool("HEADLESS", True),
        auth_state_path=_read_path("AUTH_STATE_PATH", DEFAULT_AUTH_STATE_PATH),
        data_dir=_read_path("DATA_DIR", DEFAULT_DATA_DIR),
        test_document_title=os.getenv("TEST_DOCUMENT_TITLE", "").strip(),
        test_search_keyword=os.getenv("TEST_SEARCH_KEYWORD", "").strip(),
    )


class RunOptions(BaseModel):
    """한 번의 실행 요청(batch) 설정. API와 CLI가 같은 검증을 쓴다."""

    scenario_id: str = Field(min_length=1, max_length=64)
    browser_type: BrowserType | None = None
    headless: bool | None = None
    run_count: int = Field(DEFAULT_RUN_COUNT, ge=1, le=MAX_RUN_COUNT)
    concurrency: int = Field(DEFAULT_CONCURRENCY, ge=1, le=MAX_CONCURRENCY)
    step_delay_ms: int = Field(DEFAULT_STEP_DELAY_MS, ge=0, le=MAX_STEP_DELAY_MS)
    interval_sec: float = Field(DEFAULT_INTERVAL_SEC, ge=MIN_INTERVAL_SEC, le=MAX_INTERVAL_SEC)
    timeout_sec: int = Field(DEFAULT_RUN_TIMEOUT_SEC, ge=MIN_RUN_TIMEOUT_SEC, le=MAX_RUN_TIMEOUT_SEC)
    save_success_screenshots: bool = False
    search_keyword: str | None = Field(None, max_length=100)
    # False(기본): 단계가 실패해도 기록하고 다음 단계를 계속한다. 선행 단계가 실패한 단계만 건너뛴다.
    stop_on_failure: bool = False

    def resolved_browser(self, settings: Settings) -> BrowserType:
        return self.browser_type or settings.browser_type

    def resolved_headless(self, settings: Settings) -> bool:
        return settings.headless if self.headless is None else self.headless


def limits() -> dict:
    return {
        "max_run_count": MAX_RUN_COUNT,
        "max_concurrency": MAX_CONCURRENCY,
        "min_interval_sec": MIN_INTERVAL_SEC,
        "max_interval_sec": MAX_INTERVAL_SEC,
        "max_step_delay_ms": MAX_STEP_DELAY_MS,
        "min_timeout_sec": MIN_RUN_TIMEOUT_SEC,
        "max_timeout_sec": MAX_RUN_TIMEOUT_SEC,
        "defaults": RunOptions(scenario_id="basic").model_dump(exclude={"scenario_id"}),
    }
