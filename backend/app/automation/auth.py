"""사람 보조 Google 로그인과 인증 상태 저장.

Google 로그인 화면에 테스트 계정을 입력하는 정상 절차만 수행한다. Google이 2단계 인증·CAPTCHA·
"안전하지 않은 브라우저" 확인을 요구하면 우회하지 않고 사람이 열린 브라우저에서 직접 완료한다.
Google이 자동화 브라우저의 로그인 자체를 막으면, 사람이 평소 쓰는 브라우저에서 로그인한 뒤
FixLog localStorage 토큰을 붙여 넣어 인증 상태를 만든다(build_imported_auth_state).
"""
import json
import logging

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import BrowserContext, Page, async_playwright, expect
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..config import Settings
from . import locators as loc
from .browser import launch_browser, new_context

logger = logging.getLogger(__name__)

GOOGLE_HOST = "accounts.google.com"
GOOGLE_FIELD_TIMEOUT_MS = 15_000
# Google 로그인 화면의 입력 칸과 "다음" 버튼 id. 이메일 화면은 2026-11-04 확인, 비밀번호 화면은 계정 입력이 필요해 미확인.
GOOGLE_EMAIL_INPUT = "#identifierId"
GOOGLE_EMAIL_NEXT = "#identifierNext"
GOOGLE_PASSWORD_INPUT = "input[name='Passwd']"
GOOGLE_PASSWORD_NEXT = "#passwordNext"
# FixLog가 로그인 후 localStorage에 두는 키(SPEC-20261104-fixlog-browser-automation 1장). 이 키만 받는다.
REQUIRED_TOKEN_KEY = "access_token"
IMPORTABLE_STORAGE_KEYS = ("access_token", "refresh_token", "workspace_id")


class AuthError(RuntimeError):
    pass


async def _fill_google_form(page: Page, email: str, password: str) -> None:
    """입력 칸이 보이면 채운다. 화면이 다르면(계정 선택, 추가 확인) 사람에게 맡긴다."""
    if email:
        try:
            await page.locator(GOOGLE_EMAIL_INPUT).fill(email, timeout=GOOGLE_FIELD_TIMEOUT_MS)
            await page.locator(GOOGLE_EMAIL_NEXT).click()
            logger.info("Google 이메일 입력 완료")
        except PlaywrightTimeoutError:
            logger.info("Google 이메일 입력 칸을 찾지 못했습니다. 브라우저에서 직접 진행하세요.")
            return
    if password:
        try:
            await page.locator(GOOGLE_PASSWORD_INPUT).fill(password, timeout=GOOGLE_FIELD_TIMEOUT_MS)
            await page.locator(GOOGLE_PASSWORD_NEXT).click()
            logger.info("Google 비밀번호 입력 완료")
        except PlaywrightTimeoutError:
            logger.info("Google 비밀번호 입력 칸을 찾지 못했습니다. 브라우저에서 직접 진행하세요.")


async def bootstrap_auth(settings: Settings, wait_timeout_sec: int) -> None:
    async with async_playwright() as playwright:
        # 사람이 추가 인증을 해야 할 수 있으므로 항상 화면을 띄운다.
        browser = await launch_browser(playwright, settings.browser_type, headless=False)
        try:
            context = await new_context(browser, None)
            page = await context.new_page()
            try:
                await _login_and_save(settings, context, page, wait_timeout_sec)
            except PlaywrightError as error:
                if page.is_closed():
                    raise AuthError("로그인이 끝나기 전에 브라우저 창이 닫혔습니다.") from error
                raise
        finally:
            await browser.close()


async def _login_and_save(settings: Settings, context: BrowserContext, page: Page, wait_timeout_sec: int) -> None:
    await page.goto(f"{settings.base_url}{loc.PATH_LOGIN}")
    await expect(loc.google_login_button(page)).to_be_visible()
    await loc.google_login_button(page).click()

    await page.wait_for_url(lambda u: GOOGLE_HOST in u or loc.PATH_WORKSPACE in u)
    if GOOGLE_HOST in page.url:
        await _fill_google_form(page, settings.account_email, settings.account_password)
        logger.info("Google 추가 확인이 나오면 열린 브라우저에서 직접 완료하세요. 최대 %s초 기다립니다.",
                    wait_timeout_sec)

    try:
        await page.wait_for_url(
            lambda u: u.startswith(settings.base_url) and loc.PATH_WORKSPACE in u,
            timeout=wait_timeout_sec * 1000,
        )
    except PlaywrightTimeoutError as error:
        raise AuthError(f"{wait_timeout_sec}초 안에 워크스페이스로 돌아오지 않았습니다.") from error
    await expect(loc.workspace_heading(page)).to_be_visible(timeout=30_000)

    has_token = await page.evaluate("() => Boolean(window.localStorage.getItem('access_token'))")
    if not has_token:
        raise AuthError("로그인 후 access_token을 찾지 못했습니다.")

    settings.auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(settings.auth_state_path))
    logger.info("인증 상태 저장 완료: %s", settings.auth_state_path)


def build_imported_auth_state(base_url: str, pasted_json: str) -> dict:
    """붙여 넣은 localStorage 값 JSON을 Playwright storage_state 형식으로 바꾼다.

    오류 메시지에 입력값을 넣지 않는다(토큰 노출 방지, COM-021).
    """
    try:
        pasted = json.loads(pasted_json)
    except json.JSONDecodeError as error:
        raise AuthError("붙여 넣은 값이 JSON 형식이 아닙니다.") from error
    if not isinstance(pasted, dict):
        raise AuthError("붙여 넣은 값이 JSON 객체({...})가 아닙니다.")
    unknown_keys = sorted(set(pasted) - set(IMPORTABLE_STORAGE_KEYS))
    if unknown_keys:
        raise AuthError(f"받을 수 없는 키가 있습니다: {', '.join(unknown_keys)}")
    token = pasted.get(REQUIRED_TOKEN_KEY)
    if not isinstance(token, str) or not token.strip():
        raise AuthError(f"{REQUIRED_TOKEN_KEY} 값이 없습니다. FixLog에 로그인한 탭에서 복사했는지 확인하세요.")

    local_storage = []
    for key in IMPORTABLE_STORAGE_KEYS:
        value = pasted.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise AuthError(f"{key} 값은 문자열이어야 합니다.")
        local_storage.append({"name": key, "value": value})
    return {"cookies": [], "origins": [{"origin": base_url, "localStorage": local_storage}]}


def save_imported_auth(settings: Settings, pasted_json: str) -> None:
    auth_state = build_imported_auth_state(settings.base_url, pasted_json)
    settings.auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.auth_state_path.write_text(json.dumps(auth_state, ensure_ascii=False), encoding="utf-8")
    logger.info("인증 상태 저장 완료: %s", settings.auth_state_path)
