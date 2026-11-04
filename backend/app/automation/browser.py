"""브라우저·컨텍스트 생성."""
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Playwright

from ..config import BrowserType

VIEWPORT = {"width": 1440, "height": 900}
LOCALE = "ko-KR"
TIMEZONE_ID = "Asia/Seoul"
DEFAULT_ACTION_TIMEOUT_MS = 15_000
NAVIGATION_TIMEOUT_MS = 30_000


async def launch_browser(playwright: Playwright, browser_type: BrowserType, headless: bool) -> Browser:
    launcher = getattr(playwright, browser_type)
    return await launcher.launch(headless=headless)


async def new_context(browser: Browser, auth_state_path: Path | None) -> BrowserContext:
    """저장된 로그인 상태(localStorage 토큰)가 있으면 불러온 컨텍스트를 만든다.

    User-Agent·네트워크 요청은 바꾸지 않는다. GA4 등 분석 요청도 그대로 둔다.
    """
    storage_state = str(auth_state_path) if auth_state_path and auth_state_path.exists() else None
    context = await browser.new_context(
        storage_state=storage_state,
        viewport=VIEWPORT,
        locale=LOCALE,
        timezone_id=TIMEZONE_ID,
    )
    context.set_default_timeout(DEFAULT_ACTION_TIMEOUT_MS)
    context.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
    return context
