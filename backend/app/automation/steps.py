"""브라우저 자동화 단계.

각 단계는 화면 상태(locator)가 기대한 상태가 될 때까지 기다린 뒤 검증한다. 고정 sleep을 쓰지 않는다.
단계 함수는 성공하면 기록할 설명(detail)을 돌려주고, 업무상 실패는 StepFailure로 알린다.
"""
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Page, expect
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from . import locators as loc

SUMMARY_TIMEOUT_MS = 90_000
AI_ANSWER_TIMEOUT_MS = 120_000
DOCUMENT_LOAD_TIMEOUT_MS = 30_000
# 아주 빠르게 끝나는 경우 진행 표시가 보이지 않을 수 있어, 진행 표시는 짧게만 기다린다.
PROGRESS_APPEAR_TIMEOUT_MS = 10_000
TAG_DIALOG_APPEAR_TIMEOUT_MS = 8_000
TYPING_DELAY_MS = 60
DERIVED_KEYWORD_LENGTH = 10
DETAIL_TEXT_LIMIT = 300
DEFAULT_AI_QUESTION = "최신 릴리스 체크리스트 보기"
# 문서 작성 단계가 만드는 문서. 제목은 실행마다 달라 검색 결과가 그 문서 하나로 좁혀진다.
CREATED_TITLE_PREFIX = "자동화 테스트 문서"
CREATED_TITLE_SUFFIX_LENGTH = 4
CREATED_DOCUMENT_BODY = (
    "이 문서는 FixLog 브라우저 자동화 테스트가 만든 문서입니다. "
    "배포 전에는 로그인, 문서 검색, AI 요약 기능을 순서대로 확인합니다. "
    "확인 중 오류가 나면 실패한 화면을 저장하고 담당자에게 알립니다."
)
BODY_TYPING_DELAY_MS = 10
AI_QUESTION_FOR_CREATED_DOCUMENT = "{title} 문서를 찾아줘"
REFERENCE_APPEAR_TIMEOUT_MS = 10_000

TEXT_NO_BODY_TO_SUMMARIZE = "요약할 본문이 없어요"


class StepFailure(Exception):
    """화면이 기대와 다를 때 단계 실패를 알린다."""


@dataclass
class StepContext:
    base_url: str
    has_auth_state: bool
    configured_document_title: str = ""
    configured_search_keyword: str = ""
    browser: Browser | None = None
    context: BrowserContext | None = None
    page: Page | None = None
    target_document_title: str = ""
    search_keyword: str = ""
    search_result_titles: list[str] = field(default_factory=list)
    is_search_keyword_derived: bool = False
    created_document_title: str = ""
    created_document_path: str = ""

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def require_page(self) -> Page:
        if self.page is None or self.page.is_closed():
            raise StepFailure("브라우저 페이지가 없습니다. 브라우저 종료 단계 뒤에는 다른 단계를 실행할 수 없습니다.")
        return self.page


StepFunc = Callable[[StepContext], Awaitable[str]]


@dataclass(frozen=True)
class StepDefinition:
    id: str
    name: str
    description: str
    func: StepFunc
    requires: tuple[str, ...] = ()


# ---- 공통 도우미 ----------------------------------------------------------------
def _path_of(url: str) -> str:
    return urlparse(url).path.rstrip("/") or "/"


def _is_on_path(page: Page, path: str) -> bool:
    return _path_of(page.url) == path.rstrip("/")


def _is_on_document_detail(page: Page) -> bool:
    return loc.DOCUMENT_URL_PATTERN.search(urlparse(page.url).path) is not None


def _shorten(text: str, limit: int = DETAIL_TEXT_LIMIT) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else f"{one_line[:limit]}…"


async def _wait_progress_finished(progress, timeout_ms: int) -> None:
    """진행 표시가 나타나면 사라질 때까지 기다린다. 너무 빨라 보이지 않았으면 바로 넘어간다."""
    try:
        await progress.first.wait_for(state="visible", timeout=PROGRESS_APPEAR_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return
    await expect(progress).to_have_count(0, timeout=timeout_ms)


async def _dismiss_tag_dialog(page: Page, wait_ms: int = 0) -> bool:
    """AI 요약 뒤 뜨는 "AI 추천 태그" 대화상자를 태그 추가 없이 닫는다."""
    dialog = loc.tag_dialog(page)
    try:
        await dialog.wait_for(state="visible", timeout=max(wait_ms, 1))
    except PlaywrightTimeoutError:
        return False
    await dialog.get_by_role("button", name=loc.BUTTON_CANCEL, exact=True).click()
    await expect(dialog).to_be_hidden()
    return True


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


async def _open_document_list(page: Page, ctx: StepContext) -> None:
    if not _is_on_path(page, loc.PATH_DOCUMENTS):
        nav = loc.sidebar_link(page, loc.NAV_DOCUMENTS)
        if await nav.is_visible():
            await nav.click()
        else:
            await page.goto(ctx.url(loc.PATH_DOCUMENTS))
        await page.wait_for_url(lambda u: _path_of(u) == loc.PATH_DOCUMENTS)
    await expect(loc.title_search_input(page)).to_be_visible()
    await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    list_settled = (
        loc.document_rows(page)
        .or_(loc.folder_rows(page))
        .or_(loc.empty_folder(page))
        .or_(loc.no_search_result(page))
        .first
    )
    await expect(list_settled).to_be_visible()


# ---- 1. 사이트 접속 --------------------------------------------------------------
async def open_site(ctx: StepContext) -> str:
    page = ctx.require_page()
    response = await page.goto(ctx.url(loc.PATH_LANDING), wait_until="domcontentloaded")
    if response is not None and not response.ok:
        raise StepFailure(f"사이트 응답 오류: HTTP {response.status}")
    await expect(page).to_have_title(loc.TEXT_APP_TITLE)
    await expect(page.locator("#root")).not_to_be_empty()
    return f"사이트 접속 완료 (제목: {await page.title()})"


# ---- 2. 로그인 페이지 확인 --------------------------------------------------------
async def check_login_page(ctx: StepContext) -> str:
    page = ctx.require_page()
    await page.goto(ctx.url(loc.PATH_LOGIN))
    await expect(loc.google_login_button(page)).to_be_visible()
    return f"로그인 페이지에서 '{loc.TEXT_GOOGLE_BUTTON}' 버튼 확인"


# ---- 3. 로그인 ---------------------------------------------------------------------
async def login(ctx: StepContext) -> str:
    """저장된 인증 상태로 로그인한다.

    Google OAuth는 자동화 브라우저에 추가 인증을 요구할 수 있어 무인 실행 중에는 진행하지 않는다.
    `python -m app.cli auth`로 사람이 한 번 로그인해 저장한 상태를 쓴다.
    """
    page = ctx.require_page()
    if not ctx.has_auth_state:
        raise StepFailure("저장된 로그인 상태가 없습니다. `python -m app.cli auth`로 테스트 계정 로그인을 먼저 하세요.")
    await page.goto(ctx.url(loc.PATH_WORKSPACE))
    workspace = loc.workspace_heading(page)
    login_button = loc.google_login_button(page)
    await expect(workspace.or_(login_button).first).to_be_visible(timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    if await login_button.is_visible() or _is_on_path(page, loc.PATH_LOGIN):
        raise StepFailure("로그인 상태가 만료되었습니다. `python -m app.cli auth`로 다시 로그인하세요.")
    has_token = await page.evaluate("() => Boolean(window.localStorage.getItem('access_token'))")
    if not has_token:
        raise StepFailure("워크스페이스는 열렸지만 access_token이 없습니다. 인증 상태를 다시 저장하세요.")
    return "저장된 인증 상태로 로그인 확인 (access_token 존재)"


# ---- 4. 워크스페이스 진입 -------------------------------------------------------------
async def enter_workspace(ctx: StepContext) -> str:
    page = ctx.require_page()
    if not _is_on_path(page, loc.PATH_WORKSPACE):
        nav = loc.sidebar_link(page, loc.NAV_HOME)
        if await nav.is_visible():
            await nav.click()
        else:
            await page.goto(ctx.url(loc.PATH_WORKSPACE))
        await page.wait_for_url(lambda u: _path_of(u) == loc.PATH_WORKSPACE)
    if _is_on_path(page, loc.PATH_LOGIN):
        raise StepFailure("워크스페이스 대신 로그인 페이지로 이동했습니다. 로그인 상태를 확인하세요.")
    await expect(loc.workspace_heading(page)).to_be_visible()
    await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    return "워크스페이스 홈 로드 완료"


# ---- 추가: 문서 작성 -------------------------------------------------------------
def _new_document_title() -> str:
    suffix = uuid.uuid4().hex[:CREATED_TITLE_SUFFIX_LENGTH]
    return f"{CREATED_TITLE_PREFIX} {datetime.now():%Y-%m-%d %H:%M:%S} {suffix}"


async def _wait_document_ready(page: Page) -> None:
    await expect(loc.document_loading(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    if await loc.document_error(page).count() > 0:
        raise StepFailure(f"문서 상세 오류: {await loc.document_error(page).first.inner_text()}")
    await expect(loc.document_title_input(page)).to_be_visible()
    await expect(loc.document_body_editor(page)).to_be_visible()


def _require_created_document(ctx: StepContext, page: Page) -> None:
    if not ctx.created_document_title:
        raise StepFailure("작성한 문서가 없습니다. 문서 작성 단계를 먼저 실행하세요.")
    if not _is_on_document_detail(page):
        raise StepFailure("문서 상세 화면이 아닙니다. 새 문서 만들기 단계부터 실행하세요.")


async def create_document(ctx: StepContext) -> str:
    """홈 머리글 "새 문서"를 누른다. FixLog는 대화상자 없이 '제목 없음' 문서를 만들고 편집 화면으로 이동한다."""
    page = ctx.require_page()
    if not _is_on_path(page, loc.PATH_WORKSPACE):
        await page.goto(ctx.url(loc.PATH_WORKSPACE))
    await loc.new_document_button(page).click()
    await page.wait_for_url(lambda u: loc.DOCUMENT_URL_PATTERN.search(urlparse(u).path) is not None)
    await _wait_document_ready(page)
    initial_title = await loc.document_title_input(page).input_value()
    ctx.created_document_path = urlparse(page.url).path
    return f"새 문서 생성: {urlparse(page.url).path} (처음 제목 '{initial_title}')"


async def write_document(ctx: StepContext) -> str:
    page = ctx.require_page()
    if not _is_on_document_detail(page):
        raise StepFailure("문서 상세 화면이 아닙니다. 새 문서 만들기 단계를 먼저 실행하세요.")
    title = _new_document_title()
    title_input = loc.document_title_input(page)
    await title_input.fill(title)
    await expect(title_input).to_have_value(title)

    # BlockNote 편집기는 fill을 받지 않아 사람처럼 클릭한 뒤 키보드로 입력한다.
    editor = loc.document_body_editor(page)
    await editor.click()
    await editor.press_sequentially(CREATED_DOCUMENT_BODY, delay=BODY_TYPING_DELAY_MS)
    await expect(editor).to_contain_text(CREATED_DOCUMENT_BODY)

    ctx.created_document_title = title
    ctx.target_document_title = title
    return f"제목 '{title}', 본문 {len(CREATED_DOCUMENT_BODY)}자 입력"


async def save_document(ctx: StepContext) -> str:
    page = ctx.require_page()
    _require_created_document(ctx, page)
    await loc.save_button(page).click()
    await expect(loc.save_done_toast(page)).to_be_visible(timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    return f"'{loc.TEXT_SAVE_DONE}' 알림 확인"


async def verify_saved_document(ctx: StepContext) -> str:
    """새로고침 뒤에도 제목·본문이 남는지 본다. 브라우저 임시 저장본에서 불러왔다면 서버 저장 실패로 본다."""
    page = ctx.require_page()
    _require_created_document(ctx, page)
    await page.reload()
    await _wait_document_ready(page)
    await expect(loc.document_title_input(page)).to_have_value(ctx.created_document_title)
    await expect(loc.document_body_editor(page)).to_contain_text(CREATED_DOCUMENT_BODY)
    if await loc.draft_restored_toast(page).count() > 0:
        raise StepFailure("서버 저장본이 아니라 브라우저 임시 저장본을 불러왔습니다. 저장이 서버에 반영되지 않았습니다.")
    return f"새로고침 후 제목·본문 유지 확인 ({urlparse(page.url).path})"


async def delete_document(ctx: StepContext) -> str:
    """작성한 문서만 삭제한다(휴지통으로 이동, 담당자 승인). 휴지통의 영구 삭제·복원은 하지 않는다."""
    page = ctx.require_page()
    if not ctx.created_document_title or not ctx.created_document_path:
        raise StepFailure("작성한 문서가 없습니다. 문서 작성 단계를 먼저 실행하세요.")
    if urlparse(page.url).path != ctx.created_document_path:
        # AI 의미 검색처럼 다른 화면에서 온 경우 작성한 문서로 다시 들어간다.
        await page.goto(ctx.url(ctx.created_document_path))
        await _wait_document_ready(page)
    if await loc.document_title_input(page).input_value() != ctx.created_document_title:
        raise StepFailure(f"열린 문서가 작성한 문서 '{ctx.created_document_title}'가 아니어서 삭제하지 않습니다.")
    document_path = urlparse(page.url).path

    await loc.delete_document_button(page).click()
    dialog = loc.delete_confirm_dialog(page)
    await expect(dialog).to_be_visible()
    await dialog.get_by_role("button", name=loc.BUTTON_DELETE, exact=True).click()
    await page.wait_for_url(lambda u: urlparse(u).path != document_path, timeout=DOCUMENT_LOAD_TIMEOUT_MS)

    # FixLog 목록 화면은 검색어별 결과를 메모리에 보관해, 삭제 전에 같은 검색어로 검색했으면
    # 삭제 뒤에도 옛 결과를 보여 준다(2026-11-04 실제 사이트 확인). 새로고침해 서버 결과로 확인한다.
    await _open_document_list(page, ctx)
    await page.reload()
    await _open_document_list(page, ctx)
    box = loc.title_search_input(page)
    await box.fill(ctx.created_document_title)
    await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    try:
        await expect(loc.no_search_result(page)).to_be_visible(timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    except AssertionError as error:
        if await loc.document_row_by_title(page, ctx.created_document_title).count() > 0:
            raise StepFailure(f"삭제 후에도 문서 목록에 '{ctx.created_document_title}'가 남아 있습니다.") from error
        raise
    ctx.target_document_title = ""
    return f"문서 삭제({document_path}) 후 문서 목록 검색에서 사라짐 확인"


async def verify_trash(ctx: StepContext) -> str:
    page = ctx.require_page()
    if not ctx.created_document_title:
        raise StepFailure("작성한 문서가 없습니다. 문서 작성·삭제 단계를 먼저 실행하세요.")
    nav = loc.sidebar_link(page, loc.NAV_TRASH)
    if await nav.is_visible():
        await nav.click()
    else:
        await page.goto(ctx.url(loc.PATH_TRASH))
    await page.wait_for_url(lambda u: _path_of(u) == loc.PATH_TRASH)
    await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)

    row = loc.trash_row(page, ctx.created_document_title)
    await expect(row.or_(loc.trash_empty(page)).first).to_be_visible()
    if await row.count() == 0:
        raise StepFailure(f"휴지통에 삭제한 문서 '{ctx.created_document_title}'가 없습니다.")
    await expect(row).to_contain_text(loc.TEXT_TRASHED_MARK)
    return f"휴지통에서 '{ctx.created_document_title}' 확인 ({_shorten(await row.inner_text(), 120)})"


# ---- 5. 문서 목록 조회 ------------------------------------------------------------
async def list_documents(ctx: StepContext) -> str:
    page = ctx.require_page()
    await _open_document_list(page, ctx)
    rows = loc.document_rows(page)
    document_count = await rows.count()
    folder_count = await loc.folder_rows(page).count()

    if ctx.created_document_title:
        ctx.target_document_title = ctx.created_document_title
        is_visible = await loc.document_row_by_title(page, ctx.target_document_title).count() > 0
        if not is_visible:
            raise StepFailure(f"작성한 문서 '{ctx.target_document_title}'가 문서 목록에 없습니다.")
        return f"문서 {document_count}개, 폴더 {folder_count}개. 대상 문서(작성한 문서): '{ctx.target_document_title}'"

    if ctx.configured_document_title:
        ctx.target_document_title = ctx.configured_document_title
        is_visible = await loc.document_row_by_title(page, ctx.target_document_title).count() > 0
        location = "목록에 있음" if is_visible else "최상위 목록에 없음(검색으로 찾음)"
        return f"문서 {document_count}개, 폴더 {folder_count}개. 대상 문서 '{ctx.target_document_title}' {location}"

    if document_count == 0:
        raise StepFailure(
            f"문서 목록 최상위에 문서가 없습니다(폴더 {folder_count}개). TEST_DOCUMENT_TITLE에 대상 문서 제목을 설정하세요."
        )
    ctx.target_document_title = _first_line(await rows.first.inner_text())
    return f"문서 {document_count}개, 폴더 {folder_count}개. 대상 문서: '{ctx.target_document_title}'"


# ---- 6. 검색어 입력 ---------------------------------------------------------------
async def search_input(ctx: StepContext) -> str:
    page = ctx.require_page()
    if ctx.created_document_title:
        # 작성한 문서는 제목 전체로 검색해 그 문서가 찾아지는지 확인한다.
        ctx.search_keyword = ctx.created_document_title
        ctx.is_search_keyword_derived = True
    elif ctx.configured_search_keyword:
        ctx.search_keyword = ctx.configured_search_keyword
        ctx.is_search_keyword_derived = False
    elif ctx.target_document_title:
        ctx.search_keyword = ctx.target_document_title[:DERIVED_KEYWORD_LENGTH].strip()
        ctx.is_search_keyword_derived = True
    else:
        raise StepFailure("검색어가 없습니다. TEST_SEARCH_KEYWORD를 설정하거나 문서 목록 조회 단계를 먼저 실행하세요.")

    await _open_document_list(page, ctx)
    box = loc.title_search_input(page)
    await box.click()
    await box.fill("")
    await box.press_sequentially(ctx.search_keyword, delay=TYPING_DELAY_MS)
    await expect(box).to_have_value(ctx.search_keyword)
    return f"검색어 입력: '{ctx.search_keyword}'"


# ---- 7. 검색 결과 확인 ------------------------------------------------------------
async def verify_search_results(ctx: StepContext) -> str:
    page = ctx.require_page()
    if not ctx.search_keyword:
        raise StepFailure("입력한 검색어가 없습니다. 검색어 입력 단계를 먼저 실행하세요.")
    # 입력 직후 300ms 디바운스 동안에도 "불러오는 중…"이 표시되므로 사라질 때까지 기다리면 결과가 반영된다.
    await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    settled = loc.document_rows(page).or_(loc.folder_rows(page)).or_(loc.no_search_result(page)).first
    await expect(settled).to_be_visible()

    if await loc.no_search_result(page).is_visible():
        ctx.search_result_titles = []
        if ctx.is_search_keyword_derived:
            raise StepFailure(
                f"대상 문서 제목에서 만든 검색어 '{ctx.search_keyword}'로 검색했지만 결과가 없습니다."
            )
        return f"'{ctx.search_keyword}' 검색 결과 없음 화면 확인"

    rows = loc.document_rows(page)
    titles = [_first_line(t) for t in await rows.all_inner_texts()]
    ctx.search_result_titles = titles
    is_target_found = ctx.target_document_title in titles
    if ctx.is_search_keyword_derived and not is_target_found:
        raise StepFailure(f"검색 결과 {len(titles)}건에 대상 문서 '{ctx.target_document_title}'가 없습니다.")
    preview = ", ".join(titles[:5])
    return f"'{ctx.search_keyword}' 검색 결과 문서 {len(titles)}건: {preview}"


# ---- 8. 문서 상세 진입 ------------------------------------------------------------
async def open_document(ctx: StepContext) -> str:
    page = ctx.require_page()
    if not _is_on_path(page, loc.PATH_DOCUMENTS):
        await _open_document_list(page, ctx)

    row = None
    if ctx.target_document_title:
        target_row = loc.document_row_by_title(page, ctx.target_document_title)
        if await target_row.count() > 0:
            row = target_row.first
        elif ctx.configured_document_title and not ctx.search_keyword:
            # 설정한 대상 문서가 최상위 목록에 없으면 제목 검색으로 찾아 들어간다.
            box = loc.title_search_input(page)
            await box.fill(ctx.target_document_title)
            await expect(loc.loading_indicator(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
            if await target_row.count() > 0:
                row = target_row.first
    if row is None:
        rows = loc.document_rows(page)
        if await rows.count() == 0:
            raise StepFailure("목록에 열 수 있는 문서가 없습니다.")
        row = rows.first

    clicked_title = _first_line(await row.inner_text())
    # 행 가운데에는 다른 칸(소유자, 더보기 버튼)이 올 수 있어 사람처럼 제목 글자를 누른다.
    title_text = row.get_by_text(clicked_title, exact=True)
    await (title_text.first if await title_text.count() > 0 else row).click()
    await page.wait_for_url(lambda u: loc.DOCUMENT_URL_PATTERN.search(urlparse(u).path) is not None)
    await expect(loc.document_loading(page)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    if await loc.document_error(page).count() > 0:
        message = await loc.document_error(page).first.inner_text()
        raise StepFailure(f"문서 상세 오류: {message}")
    title_input = loc.document_title_input(page)
    await expect(title_input).to_be_visible()
    opened_title = await title_input.input_value()
    ctx.target_document_title = opened_title or clicked_title
    return f"문서 상세 진입: '{ctx.target_document_title}' ({urlparse(page.url).path})"


# ---- 9. AI 요약 실행 --------------------------------------------------------------
async def ai_summary(ctx: StepContext) -> str:
    """요약 버튼은 FixLog 동작상 문서를 먼저 저장한 뒤 요약한다(버전 기록이 생길 수 있음, 담당자 승인)."""
    page = ctx.require_page()
    if not _is_on_document_detail(page):
        raise StepFailure("문서 상세 화면이 아닙니다. 문서 상세 진입 단계를 먼저 실행하세요.")
    await _dismiss_tag_dialog(page)

    await loc.summarize_button(page).click()
    panel = loc.ai_panel(page)
    await expect(panel).to_be_visible()
    await _wait_progress_finished(panel.get_by_text(loc.TEXT_SUMMARIZING), SUMMARY_TIMEOUT_MS)

    if await page.get_by_text(TEXT_NO_BODY_TO_SUMMARIZE).count() > 0:
        raise StepFailure("문서 본문이 비어 있어 요약할 수 없습니다.")
    if await panel.get_by_text(loc.TEXT_SUMMARY_FAILED, exact=True).count() > 0:
        raise StepFailure(loc.TEXT_SUMMARY_FAILED)
    if await panel.get_by_text(loc.TEXT_SUMMARY_EMPTY, exact=True).count() > 0:
        raise StepFailure(loc.TEXT_SUMMARY_EMPTY)

    summary = _extract_summary_text(await panel.inner_text())
    if not summary:
        raise StepFailure("요약 패널에 요약 본문이 없습니다.")

    closed_tag_dialog = await _dismiss_tag_dialog(page, TAG_DIALOG_APPEAR_TIMEOUT_MS)
    await loc.close_panel_button(panel).click()
    await expect(panel).to_be_hidden()
    note = " / 추천 태그 대화상자는 추가 없이 닫음" if closed_tag_dialog else ""
    return f"요약 결과({len(summary)}자): {_shorten(summary)}{note}"


def _extract_summary_text(panel_text: str) -> str:
    header_lines = {loc.TEXT_AI_PANEL_TITLE, loc.TEXT_SUMMARY_SECTION}
    lines = []
    for line in panel_text.splitlines():
        stripped = line.strip()
        if stripped == loc.TEXT_ASK_AI_SECTION:
            break
        if stripped and stripped not in header_lines:
            lines.append(stripped)
    return "\n".join(lines)


# ---- 10. 버전 기록 조회 -----------------------------------------------------------
async def version_history(ctx: StepContext) -> str:
    """버전 기록 패널을 열고 가장 최근 이전 버전을 미리보기(읽기 전용)한 뒤 현재 버전으로 돌아온다.
    복원 버튼은 누르지 않는다."""
    page = ctx.require_page()
    if not _is_on_document_detail(page):
        raise StepFailure("문서 상세 화면이 아닙니다. 문서 상세 진입 단계를 먼저 실행하세요.")
    await _dismiss_tag_dialog(page)

    panel = loc.history_panel(page)
    if not await panel.is_visible():
        await loc.history_button(page).click()
    await expect(panel).to_be_visible()
    await expect(panel.get_by_text(loc.TEXT_LOADING)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)

    items = loc.history_items(panel)
    empty = panel.get_by_text(loc.TEXT_HISTORY_EMPTY)
    failed = panel.get_by_text(loc.TEXT_HISTORY_FAILED, exact=True)
    await expect(items.or_(empty).or_(failed).first).to_be_visible()

    if await failed.count() > 0:
        raise StepFailure(loc.TEXT_HISTORY_FAILED)
    if await empty.count() > 0:
        await loc.close_panel_button(panel).click()
        return "버전 기록 패널 확인: 이전 버전 없음"

    version_count = await items.count()
    latest = items.first
    latest_text = _shorten(await latest.inner_text(), 120)
    await latest.click()
    banner = loc.version_preview_banner(page)
    await expect(banner).to_be_visible()
    await expect(page.get_by_text(loc.TEXT_VERSION_PREVIEW_LOADING)).to_have_count(0, timeout=DOCUMENT_LOAD_TIMEOUT_MS)
    if await page.get_by_text(loc.TEXT_VERSION_PREVIEW_LOAD_FAILED, exact=True).count() > 0:
        raise StepFailure(loc.TEXT_VERSION_PREVIEW_LOAD_FAILED)
    banner_text = _shorten(await banner.inner_text(), 120)

    await loc.back_to_current_button(page).click()
    await expect(banner).to_be_hidden()
    await loc.close_panel_button(panel).click()
    await expect(panel).to_be_hidden()
    return f"이전 버전 {version_count}개. 최근 이전 버전 [{latest_text}] 미리보기 확인({banner_text}) 후 현재 버전으로 복귀"


# ---- 11. 다른 페이지 이동 ---------------------------------------------------------
async def navigate_other_page(ctx: StepContext) -> str:
    page = ctx.require_page()
    from_path = urlparse(page.url).path
    await _dismiss_tag_dialog(page)
    if _is_on_path(page, loc.PATH_WORKSPACE):
        await loc.sidebar_link(page, loc.NAV_DOCUMENTS).click()
        await page.wait_for_url(lambda u: _path_of(u) == loc.PATH_DOCUMENTS)
        await expect(loc.title_search_input(page)).to_be_visible()
    else:
        await loc.sidebar_link(page, loc.NAV_HOME).click()
        await page.wait_for_url(lambda u: _path_of(u) == loc.PATH_WORKSPACE)
        await expect(loc.workspace_heading(page)).to_be_visible()
    return f"페이지 이동: {from_path} → {urlparse(page.url).path}"


# ---- 12. 브라우저 종료 -----------------------------------------------------------
async def close_browser(ctx: StepContext) -> str:
    if ctx.context is not None:
        await ctx.context.close()
    if ctx.browser is not None:
        await ctx.browser.close()
    ctx.page = None
    ctx.context = None
    ctx.browser = None
    return "브라우저 종료"


# ---- 추가: AI 의미 검색 -----------------------------------------------------------
async def ai_search(ctx: StepContext) -> str:
    """워크스페이스 홈에서 AI 검색 질문을 보낸다. FixLog 서버에 대화방이 생성된다(담당자 승인)."""
    page = ctx.require_page()
    if not _is_on_path(page, loc.PATH_WORKSPACE):
        await page.goto(ctx.url(loc.PATH_WORKSPACE))
    if ctx.created_document_title:
        question = AI_QUESTION_FOR_CREATED_DOCUMENT.format(title=ctx.created_document_title)
    else:
        question = ctx.configured_search_keyword or DEFAULT_AI_QUESTION
    box = loc.home_ai_search_input(page)
    await expect(box).to_be_visible()
    await box.click()
    await box.press_sequentially(question, delay=TYPING_DELAY_MS)
    await loc.home_ai_search_submit(page).click()

    await page.wait_for_url(lambda u: _path_of(u).startswith(loc.PATH_SEARCH))
    await expect(page.get_by_text(question, exact=True).first).to_be_visible()
    await _wait_progress_finished(loc.answer_generating(page), AI_ANSWER_TIMEOUT_MS)
    if await loc.answer_failed(page).count() > 0:
        raise StepFailure(loc.TEXT_AI_ANSWER_FAILED)
    if ctx.created_document_title:
        return await _verify_created_document_referenced(ctx, page, question)
    reference_count = await page.get_by_text(loc.BUTTON_OPEN_REFERENCE).count()
    return f"AI 검색 질문 '{question}' 답변 수신 (근거 문서 링크 {reference_count}개, {urlparse(page.url).path})"


async def _verify_created_document_referenced(ctx: StepContext, page: Page, question: str) -> str:
    """작성한 문서를 물었으면 답변 근거 문서 카드에 그 문서가 나와야 한다."""
    reference = loc.ai_reference_by_title(page, ctx.created_document_title)
    try:
        await expect(reference.first).to_be_visible(timeout=REFERENCE_APPEAR_TIMEOUT_MS)
    except AssertionError as error:
        titles = [t.strip() for t in await loc.ai_reference_titles(page).all_inner_texts()]
        found = ", ".join(titles) if titles else "없음"
        raise StepFailure(
            f"AI 검색 근거 문서에 작성한 문서 '{ctx.created_document_title}'가 없습니다. 근거 문서: {found}"
        ) from error
    total = await loc.ai_reference_titles(page).count()
    return f"AI 검색 질문 '{question}' 답변의 근거 문서 {total}건 중 작성한 문서 확인 ({urlparse(page.url).path})"


LOGIN = ("login",)

# requires: 이 실행에서 이 단계들이 실패하거나 건너뛰어졌으면 이 단계도 건너뛴다.
# 시나리오에 없는 선행 단계는 따지지 않는다(단계 안의 확인이 처리한다).
STEP_DEFINITIONS: tuple[StepDefinition, ...] = (
    StepDefinition("open_site", "사이트 접속", "FixLog 메인 페이지 접속 후 제목 확인", open_site),
    StepDefinition("check_login_page", "로그인 페이지 확인", "/login에서 Google 로그인 버튼 확인", check_login_page),
    StepDefinition("login", "로그인", "저장된 테스트 계정 인증 상태로 워크스페이스 접근 확인", login),
    StepDefinition("enter_workspace", "워크스페이스 진입", "홈 화면과 최근 문서 로드 확인", enter_workspace, LOGIN),
    StepDefinition("list_documents", "문서 목록 조회", "사이드바 '문서' 이동 후 목록 확인, 대상 문서 선택",
                   list_documents, LOGIN),
    StepDefinition("search_input", "검색어 입력", "문서 목록 제목 검색창에 검색어 입력", search_input, LOGIN),
    StepDefinition("verify_search_results", "검색 결과 확인", "검색 결과 또는 결과 없음 화면 확인",
                   verify_search_results, ("search_input",)),
    StepDefinition("open_document", "문서 상세 진입", "대상 문서(또는 첫 문서) 클릭 후 상세 로드 확인",
                   open_document, LOGIN),
    StepDefinition("ai_summary", "AI 요약 실행", "요약 버튼 클릭 후 요약 결과 확인(문서 저장 발생)",
                   ai_summary, ("open_document",)),
    StepDefinition("version_history", "버전 기록 조회", "버전 기록 패널, 이전 버전 미리보기 후 현재 버전 복귀",
                   version_history, ("open_document",)),
    StepDefinition("navigate_other_page", "다른 페이지 이동", "사이드바로 다른 화면 이동", navigate_other_page, LOGIN),
    StepDefinition("close_browser", "브라우저 종료", "브라우저 컨텍스트와 브라우저 종료", close_browser),
    StepDefinition("ai_search", "AI 의미 검색", "홈에서 AI 검색 질문 후 답변 확인(대화방 생성)", ai_search, LOGIN),
    StepDefinition("create_document", "새 문서 만들기", "홈 '새 문서' 버튼으로 문서 생성 후 편집 화면 확인",
                   create_document, LOGIN),
    StepDefinition("write_document", "문서 작성", "제목·본문 입력", write_document, ("create_document",)),
    StepDefinition("save_document", "문서 저장", "'저장' 버튼 클릭 후 저장 완료 알림 확인",
                   save_document, ("write_document",)),
    StepDefinition("verify_saved_document", "저장 내용 확인", "새로고침 후 제목·본문 유지 확인",
                   verify_saved_document, ("save_document",)),
    StepDefinition("delete_document", "문서 삭제", "작성한 문서 삭제(휴지통 이동) 후 문서 목록에서 사라짐 확인",
                   delete_document, ("write_document",)),
    StepDefinition("verify_trash", "휴지통 확인", "휴지통에 삭제한 문서가 있는지 확인(영구 삭제 안 함)",
                   verify_trash, ("delete_document",)),
)

STEP_REGISTRY: dict[str, StepDefinition] = {step.id: step for step in STEP_DEFINITIONS}
CLOSE_BROWSER_STEP_ID = "close_browser"
