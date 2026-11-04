"""FixLog 화면 locator 모음.

2026-11-04 배포 번들(assets/index-CznndP-r.js와 lazy chunk)에서 확인한 실제 화면 문구·aria-label·
placeholder만 쓴다. Tailwind 클래스명은 배포마다 바뀔 수 있어 쓰지 않는다.
FixLog 화면 문구가 바뀌면 이 파일만 고친다.
"""
import re

from playwright.async_api import Locator, Page

# ---- 경로 -------------------------------------------------------------------
PATH_LANDING = "/"
PATH_LOGIN = "/login"
PATH_WORKSPACE = "/workspace"
PATH_DOCUMENTS = "/documents"
PATH_SEARCH = "/search"
PATH_TRASH = "/trash"

DOCUMENT_URL_PATTERN = re.compile(r"/documents/[^/?#]+")
SEARCH_CONVERSATION_URL_PATTERN = re.compile(r"/search(/[^/?#]+)?")

# ---- 화면 문구 ----------------------------------------------------------------
TEXT_APP_TITLE = "FixLog"
TEXT_GOOGLE_BUTTON = "Continue with Google"
TEXT_LOGIN_PROCESSING = "로그인 처리 중..."
TEXT_LOADING = "불러오는 중…"
TEXT_WORKSPACE_HEADING = "무엇을 찾고 계신가요?"
TEXT_DOCUMENT_TYPE = "문서"
TEXT_FOLDER_TYPE = "폴더"
TEXT_NO_SEARCH_RESULT = "검색 결과가 없습니다."
TEXT_EMPTY_FOLDER = "폴더가 비었습니다."
TEXT_DOCUMENT_LOADING = "문서를 불러오는 중…"
TEXT_DOCUMENT_FORBIDDEN = "문서에 접근할 권한이 없습니다."
TEXT_DOCUMENT_LOAD_FAILED = "문서를 불러오지 못했습니다."
TEXT_AI_PANEL_TITLE = "문서 AI"
TEXT_SUMMARIZING = "요약하는 중…"
TEXT_SUMMARY_FAILED = "AI 요약에 실패했습니다. 잠시 후 다시 시도해 주세요."
TEXT_SUMMARY_EMPTY = "요약 결과가 비어 있습니다."
TEXT_SUMMARY_SECTION = "요약"
TEXT_ASK_AI_SECTION = "AI에게 질문"
TEXT_TAG_DIALOG_TITLE = "AI 추천 태그"
TEXT_HISTORY_PANEL_TITLE = "버전 기록"
TEXT_HISTORY_EMPTY = "아직 이전 버전이 없습니다."
TEXT_HISTORY_FAILED = "버전 기록을 불러오지 못했습니다."
TEXT_VERSION_PREVIEW_BANNER = "버전을 보고 있어요 · 읽기 전용"
TEXT_VERSION_PREVIEW_LOADING = "이 버전의 본문을 불러오는 중…"
TEXT_VERSION_PREVIEW_LOAD_FAILED ="이 버전의 본문을 불러오지 못했습니다."
TEXT_AI_ANSWER_FAILED = "답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
TEXT_SAVE_DONE = "문서를 저장했어요."
TEXT_DRAFT_RESTORED = "임시 저장본을 불러왔어요."
TEXT_DELETE_CONFIRM_TITLE = "삭제하시겠습니까?"
TEXT_TRASH_EMPTY = "휴지통이 비어 있습니다."
TEXT_TRASHED_MARK = "삭제됨"

PLACEHOLDER_HOME_AI_SEARCH = "FixLog에게 필요한 문서를 찾아달라고 해보세요..."
PLACEHOLDER_TITLE_SEARCH = "제목으로 검색..."

LABEL_HOME_SEARCH_SUBMIT = "검색"
LABEL_DOCUMENT_TITLE = "문서 제목"
LABEL_HISTORY_BUTTON = "버전 기록"
LABEL_CLOSE_PANEL = "패널 닫기"
LABEL_ANSWER_GENERATING = "답변 생성 중"
LABEL_DELETE_DOCUMENT = "문서 삭제"

BUTTON_SUMMARIZE = "요약"
BUTTON_BACK_TO_CURRENT = "현재 버전으로 돌아가기"
BUTTON_CANCEL = "취소"
BUTTON_NEW_DOCUMENT = "새 문서"
BUTTON_SAVE = "저장"
BUTTON_DELETE = "삭제"
BUTTON_RESTORE = "복원"
BUTTON_OPEN_REFERENCE = "문서 열기"

# 본문 편집기는 BlockNote 라이브러리가 만드는 contenteditable 요소다(라이브러리 고정 클래스명).
SELECTOR_BODY_EDITOR = ".bn-editor"

NAV_HOME = "홈"
NAV_AI_SEARCH = "AI 검색"
NAV_DOCUMENTS = "문서"
NAV_TRASH = "휴지통"


# ---- 로그인 ------------------------------------------------------------------
def google_login_button(page: Page) -> Locator:
    return page.get_by_role("button", name=TEXT_GOOGLE_BUTTON)


# ---- 공통 ---------------------------------------------------------------------
def loading_indicator(page: Page) -> Locator:
    return page.get_by_text(TEXT_LOADING, exact=True)


def sidebar_link(page: Page, label: str) -> Locator:
    # 사이드바에는 문서 제목 링크도 함께 있으므로 메뉴 이름과 정확히 같은 링크만 고른다.
    return page.get_by_role("link", name=label, exact=True).first


# ---- 워크스페이스 홈 -----------------------------------------------------------
def workspace_heading(page: Page) -> Locator:
    return page.get_by_role("heading", name=TEXT_WORKSPACE_HEADING)


def home_ai_search_input(page: Page) -> Locator:
    return page.get_by_placeholder(PLACEHOLDER_HOME_AI_SEARCH)


def home_ai_search_submit(page: Page) -> Locator:
    return page.get_by_role("button", name=LABEL_HOME_SEARCH_SUBMIT, exact=True)


def new_document_button(page: Page) -> Locator:
    """홈 머리글의 "새 문서" 버튼. 빠른 실행 카드에도 같은 이름이 있어 <header> 안에서 찾는다."""
    return page.locator("header").get_by_role("button", name=BUTTON_NEW_DOCUMENT, exact=True)


# ---- 문서 목록 ----------------------------------------------------------------
def title_search_input(page: Page) -> Locator:
    return page.get_by_placeholder(PLACEHOLDER_TITLE_SEARCH)


def document_rows(page: Page) -> Locator:
    """문서 행. 폴더 행과 같은 role=button이므로 유형 칸 문구 "문서"로 구분한다."""
    return page.get_by_role("button").filter(
        has=page.get_by_text(TEXT_DOCUMENT_TYPE, exact=True)
    )


def folder_rows(page: Page) -> Locator:
    return page.get_by_role("button").filter(
        has=page.get_by_text(TEXT_FOLDER_TYPE, exact=True)
    )


def document_row_by_title(page: Page, title: str) -> Locator:
    return document_rows(page).filter(has=page.get_by_text(title, exact=True))


def no_search_result(page: Page) -> Locator:
    return page.get_by_text(TEXT_NO_SEARCH_RESULT, exact=True)


def empty_folder(page: Page) -> Locator:
    return page.get_by_text(TEXT_EMPTY_FOLDER, exact=True)


# ---- 문서 상세 ----------------------------------------------------------------
def document_title_input(page: Page) -> Locator:
    return page.get_by_label(LABEL_DOCUMENT_TITLE, exact=True)


def document_loading(page: Page) -> Locator:
    return page.get_by_text(TEXT_DOCUMENT_LOADING, exact=True)


def document_error(page: Page) -> Locator:
    return page.get_by_text(TEXT_DOCUMENT_FORBIDDEN, exact=True).or_(
        page.get_by_text(TEXT_DOCUMENT_LOAD_FAILED, exact=True)
    )


def document_body_editor(page: Page) -> Locator:
    return page.locator(SELECTOR_BODY_EDITOR)


def save_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BUTTON_SAVE, exact=True)


def save_done_toast(page: Page) -> Locator:
    return page.get_by_text(TEXT_SAVE_DONE, exact=True)


def draft_restored_toast(page: Page) -> Locator:
    return page.get_by_text(TEXT_DRAFT_RESTORED, exact=True)


def delete_document_button(page: Page) -> Locator:
    return page.get_by_role("button", name=LABEL_DELETE_DOCUMENT, exact=True)


def delete_confirm_dialog(page: Page) -> Locator:
    return page.get_by_role("alertdialog").filter(has=page.get_by_text(TEXT_DELETE_CONFIRM_TITLE, exact=True))


def summarize_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BUTTON_SUMMARIZE, exact=True)


def side_panel(page: Page, title: str) -> Locator:
    # 우측 패널은 <aside> 요소이고 첫 줄에 패널 제목이 있다.
    return page.locator("aside").filter(has=page.get_by_text(title, exact=True))


def ai_panel(page: Page) -> Locator:
    return side_panel(page, TEXT_AI_PANEL_TITLE)


def tag_dialog(page: Page) -> Locator:
    return page.get_by_role("dialog").filter(has=page.get_by_text(TEXT_TAG_DIALOG_TITLE, exact=True))


def history_button(page: Page) -> Locator:
    return page.get_by_role("button", name=LABEL_HISTORY_BUTTON, exact=True)


def history_panel(page: Page) -> Locator:
    return side_panel(page, TEXT_HISTORY_PANEL_TITLE)


def history_items(panel: Locator) -> Locator:
    """이전 버전 항목. "현재 버전" 버튼은 목록(li) 밖에 있다."""
    return panel.locator("li").get_by_role("button")


def version_preview_banner(page: Page) -> Locator:
    return page.get_by_text(TEXT_VERSION_PREVIEW_BANNER)


def back_to_current_button(page: Page) -> Locator:
    return page.get_by_role("button", name=BUTTON_BACK_TO_CURRENT)


def close_panel_button(panel: Locator) -> Locator:
    return panel.get_by_role("button", name=LABEL_CLOSE_PANEL)


# ---- 휴지통 -------------------------------------------------------------------
def trash_row(page: Page, title: str) -> Locator:
    """휴지통 항목 행. 이름과 "복원" 버튼을 함께 가진 요소 중 가장 안쪽(문서 순서상 마지막) 요소."""
    return (
        page.locator("div")
        .filter(has=page.get_by_text(title, exact=True))
        .filter(has=page.get_by_role("button", name=BUTTON_RESTORE))
        .last
    )


def trash_empty(page: Page) -> Locator:
    return page.get_by_text(TEXT_TRASH_EMPTY, exact=True)


# ---- AI 검색 ------------------------------------------------------------------
def answer_generating(page: Page) -> Locator:
    return page.get_by_role("status", name=LABEL_ANSWER_GENERATING)


def ai_reference_titles(page: Page) -> Locator:
    """AI 답변의 근거 문서 카드 제목(h3). 카드마다 "문서 열기" 버튼이 있다."""
    return page.get_by_role("heading", level=3)


def ai_reference_by_title(page: Page, title: str) -> Locator:
    return page.get_by_role("heading", level=3, name=title, exact=True)


def answer_failed(page: Page) -> Locator:
    return page.get_by_text(TEXT_AI_ANSWER_FAILED, exact=True)
