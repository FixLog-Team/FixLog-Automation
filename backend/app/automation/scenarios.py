"""시나리오 = 단계 ID 목록. 기본 시나리오와 대시보드에서 만든 사용자 정의 시나리오를 함께 다룬다."""
import uuid
from dataclasses import asdict, dataclass

from ..service import RunRecordService
from .steps import STEP_REGISTRY

MAX_CUSTOM_STEPS = 30


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    steps: tuple[str, ...]
    is_builtin: bool = True

    def to_dict(self) -> dict:
        return {**asdict(self), "steps": list(self.steps)}


BUILTIN_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "basic", "기본 탐색", "메인 페이지 접속 → 워크스페이스 → 문서 목록 → 문서 상세",
        ("open_site", "login", "enter_workspace", "list_documents", "open_document", "close_browser"),
    ),
    Scenario(
        "search", "검색", "워크스페이스 진입 → 제목 검색어 입력 → 검색 결과 확인 → 결과 문서 진입",
        ("login", "enter_workspace", "list_documents", "search_input", "verify_search_results",
         "open_document", "close_browser"),
    ),
    Scenario(
        "ai", "AI 기능", "문서 상세 진입 → AI 요약 실행 → 요약 결과 확인 (문서 저장 발생)",
        ("login", "list_documents", "open_document", "ai_summary", "close_browser"),
    ),
    Scenario(
        "version", "버전 관리", "문서 진입 → 버전 기록 조회 → 이전 버전 미리보기 확인 (복원 안 함)",
        ("login", "list_documents", "open_document", "version_history", "close_browser"),
    ),
    Scenario(
        "ai_search", "AI 의미 검색", "워크스페이스 홈에서 AI 검색 질문 → 답변 확인 (대화방 생성)",
        ("login", "enter_workspace", "ai_search", "close_browser"),
    ),
    Scenario(
        "write", "문서 작성·삭제",
        "새 문서 만들기 → 제목·본문 작성 → 저장 → 저장 내용 확인 → 삭제 → 휴지통 확인 (휴지통에 문서가 남음)",
        ("login", "enter_workspace", "create_document", "write_document", "save_document",
         "verify_saved_document", "delete_document", "verify_trash", "close_browser"),
    ),
    Scenario(
        "full", "전체 사용자 여정",
        "접속·로그인 → 문서 작성·저장 → 작성한 문서 검색·상세 → AI 요약 → 버전 기록 → 작성한 문서 AI 의미 검색"
        " → 문서 삭제·휴지통 확인 → 다른 페이지 이동 (휴지통 문서·대화방이 남음)",
        ("open_site", "check_login_page", "login", "enter_workspace", "create_document", "write_document",
         "save_document", "verify_saved_document", "list_documents", "search_input", "verify_search_results",
         "open_document", "ai_summary", "version_history", "ai_search", "delete_document", "verify_trash",
         "navigate_other_page", "close_browser"),
    ),
)

_BUILTIN_BY_ID = {s.id: s for s in BUILTIN_SCENARIOS}


class ScenarioError(ValueError):
    """시나리오 입력이 잘못되었을 때."""


def list_scenarios(records: RunRecordService) -> list[Scenario]:
    custom = [
        Scenario(row["id"], row["name"], row["description"], tuple(row["steps"]), is_builtin=False)
        for row in records.get_custom_scenario_list()
    ]
    return [*BUILTIN_SCENARIOS, *custom]


def find_scenario(records: RunRecordService, scenario_id: str) -> Scenario | None:
    if scenario_id in _BUILTIN_BY_ID:
        return _BUILTIN_BY_ID[scenario_id]
    return next((s for s in list_scenarios(records) if s.id == scenario_id), None)


def create_custom_scenario(records: RunRecordService, name: str, description: str, steps: list[str]) -> Scenario:
    unknown = [step for step in steps if step not in STEP_REGISTRY]
    if unknown:
        raise ScenarioError(f"알 수 없는 단계: {', '.join(unknown)}")
    if not 1 <= len(steps) <= MAX_CUSTOM_STEPS:
        raise ScenarioError(f"단계는 1~{MAX_CUSTOM_STEPS}개여야 합니다.")
    scenario_id = f"custom-{uuid.uuid4().hex[:8]}"
    records.add_custom_scenario(scenario_id, name.strip(), description.strip(), steps)
    return Scenario(scenario_id, name.strip(), description.strip(), tuple(steps), is_builtin=False)


def delete_custom_scenario(records: RunRecordService, scenario_id: str) -> bool:
    if scenario_id in _BUILTIN_BY_ID:
        raise ScenarioError("기본 시나리오는 삭제할 수 없습니다.")
    return records.remove_custom_scenario(scenario_id)
