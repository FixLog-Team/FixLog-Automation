# SPEC-20261104-document-write-scenario 문서 작성 시나리오

| 항목 | 값 |
|------|----|
| 상태 | 확정 |
| 담당자 | 프로젝트 담당자 |
| 유형 | 신규 |

## 1. 목적

FixLog에서 새 문서를 만들고 제목·본문을 써서 저장한 뒤, 그 문서로 검색·AI 요약·버전 기록까지 이어지는 사용자 여정을 자동으로 확인한다.
기존 시나리오는 이미 있는 문서만 읽기 때문에 문서 생성·편집·저장 기능은 확인하지 못한다.

## 2. 요구 사항

- 대상 화면·기능
  - FixLog 홈(`/workspace`)의 "새 문서" 버튼
  - 문서 편집 화면(`/documents/{id}`)
  - 이 프로그램: `backend/app/automation/steps.py`, `scenarios.py`, `locators.py`
- 현재: 없음. 기존 시나리오(SPEC-20261104-fixlog-browser-automation)는 문서 목록의 첫 문서나 `TEST_DOCUMENT_TITLE` 문서만 사용한다.
- FixLog 화면 분석 결과(2026-11-04, 배포 번들 `WorkspaceHomePage`·`DocumentEditorPage`·`ShareDialog` 청크 확인)
  - 홈 머리글의 "새 문서" 버튼: 최상위(folderId 없음)에 제목 "제목 없음" 문서를 바로 만들고 `/documents/{id}`로 이동한다. 대화상자는 없다. 홈 빠른 실행 카드에도 같은 이름 "새 문서"가 있다.
  - 제목 입력: `input[aria-label="문서 제목"]`, placeholder "제목을 입력하세요"
  - 본문: BlockNote 편집기(`.bn-editor`, contenteditable)
  - 저장: 머리글 "저장" 버튼(저장 중에는 "저장 중…"). 성공하면 알림 "문서를 저장했어요.". Ctrl+S도 같은 동작이다.
  - 저장하지 않은 변경은 브라우저 localStorage에만 임시 저장된다("임시 저장했어요."). 서버에 저장되지 않는다.
  - 머리글에 삭제 버튼이 있다. 삭제하면 문서가 휴지통으로 간다.
- 변경 후
  - 새 단계 4개
    | 단계 ID | 이름 | 동작 | 성공 기준 |
    |--------|------|------|----------|
    | create_document | 새 문서 만들기 | 홈 머리글 "새 문서" 클릭 | `/documents/{id}`로 이동, 제목 칸이 보임 |
    | write_document | 문서 작성 | 제목 칸에 제목 입력, 본문 편집기에 본문 입력 | 제목 칸 값이 입력한 제목과 같고 본문에 입력한 글이 보임 |
    | save_document | 문서 저장 | "저장" 버튼 클릭 | 알림 "문서를 저장했어요." 표시 |
    | verify_saved_document | 저장 내용 확인 | 문서 페이지 새로고침 | 새로고침 뒤에도 제목과 본문이 남아 있음 |
  - 제목: `자동화 테스트 문서 YYYY-MM-DD HH:MM:SS` (실행마다 다르게 만들어 검색 결과가 1건이 되게 한다)
  - 제목 끝에 임의 4자리를 붙여 동시 실행끼리도 제목이 겹치지 않게 한다.
  - 본문: 코드에 고정한 예시 글 3문장(담당자: 내용은 아무거나). AI 요약이 "요약할 본문이 없어요"로 실패하지 않을 만큼 쓴다.
  - 문서를 만든 실행에서는 그 문서를 대상 문서로 쓴다. 문서 목록 조회 단계는 `TEST_DOCUMENT_TITLE`보다 이 문서를 먼저 고른다.
  - 새 기본 시나리오 `write`(문서 작성): 로그인 → 워크스페이스 진입 → 새 문서 만들기 → 문서 작성 → 문서 저장 → 저장 내용 확인 → 브라우저 종료
  - 기본 시나리오 `full`(전체 사용자 여정)을 모든 흐름으로 바꾼다(담당자 지시)
    - 사이트 접속 → 로그인 페이지 확인 → 로그인 → 워크스페이스 진입 → 새 문서 만들기 → 문서 작성 → 문서 저장 → 저장 내용 확인 → 문서 목록 조회 → 검색어 입력 → 검색 결과 확인 → 문서 상세 진입 → AI 요약 실행 → 버전 기록 조회 → AI 의미 검색 → 다른 페이지 이동 → 브라우저 종료
  - 작성한 문서는 제목 전체로 검색한다(검색 결과가 그 문서 1건)
  - 새 단계는 대시보드의 사용자 정의 시나리오에서도 고를 수 있다(기존 단계 목록 API가 자동으로 포함한다).
- 범위 밖
  - 폴더 만들기, 문서 가져오기, 공유, 다운로드
  - 만든 문서를 삭제·휴지통에서 복원하기(4장 질문)
  - 대시보드 화면 변경(시나리오·단계 목록은 API에서 받아 자동 표시)
  - 후속 과제: 버전 기록 단계 결과에 버전 번호와 날짜가 붙어 출력됨(`[v52026년 …]`). 표시 형식만의 문제라 이번에 고치지 않는다

## 3. 완료 기준

- 전제: `backend/.auth/state.json`에 로그인 상태가 저장되어 있다. 실제 사이트 확인은 실행 횟수 1, 동시 실행 1로 한다(PRJ-005)

| # | 입력·동작 | 기대 결과 |
|---|----------|----------|
| 1 | `cli scenarios` | 목록에 `write 문서 작성`이 있다 |
| 2 | `cli run --scenario write --count 1` | 7단계가 모두 PASSED이고, 새 문서 만들기 단계 설명에 문서 URL이 남는다 |
| 3 | 실행 후 FixLog 문서 목록에서 `자동화 테스트 문서 …` 검색 | 문서가 1건 있고 본문이 남아 있다 |
| 4 | `cli run --scenario full --count 1` | 17단계가 모두 PASSED이고, 검색 결과 확인 단계에서 작성한 문서 제목으로 1건이 찾아진다 |
| 5 | 대시보드 시나리오 화면 | `문서 작성` 시나리오가 보이고 실행할 수 있다. 사용자 정의 시나리오 단계 목록에 새 단계 4개가 있다 |
| 6 | `pytest` | 가짜 FixLog 화면으로 새 단계 4개와 `write` 시나리오 테스트를 포함해 모두 통과 |

## 4. 미결 사항

- 만든 문서 처리 — 가정: 삭제하지 않는다(담당자 결정). 쌓인 문서는 담당자가 FixLog에서 직접 지운다
- 제목·본문 설정 — 가정: 코드에 고정한다(담당자 결정: "내용은 아무거나")

## 5. 구현 계획

### 5.1 수정 파일

| 파일 | 구분(신규/수정/삭제/이름 변경) | 변경 내용 |
|------|------------------------------|----------|
| `backend/app/automation/locators.py` | 수정 | 홈 머리글 "새 문서" 버튼, 본문 편집기, "저장" 버튼, 저장 알림 문구 |
| `backend/app/automation/steps.py` | 수정 | 단계 4개 추가, `StepContext`에 만든 문서 제목·본문 추가, 문서 목록 조회 단계에서 만든 문서를 대상으로 선택 |
| `backend/app/automation/scenarios.py` | 수정 | 기본 시나리오 `write` 추가, `full`에 문서 작성·AI 의미 검색 추가 |
| `backend/tests/fixture_site/index.html` | 수정 | 가짜 화면에 새 문서 만들기·편집·저장·새로고침 후 유지 추가 |
| `backend/tests/test_steps_fixture.py` | 수정 | 새 단계와 `write`·`full` 시나리오 테스트, 문서를 만들지 않는 기존 여정 테스트 |
| `docs/ai/domain.md` | 수정 | 업무 규칙(만든 문서를 대상 문서로 사용, 실행마다 문서가 생김) |
| `README.md` | 수정 | 시나리오 목록에 `write` 추가 |
| `docs/specs/SPEC-20261104-document-write-scenario.md` | 신규 | 이 명세 |

### 5.2 처리 방식·영향 범위

- 참고 코드: `steps.py`의 `ai_summary`(버튼 클릭 → 알림·결과 대기), `open_document`(상세 로드 대기)
- 처리 순서
  1. `create_document`: `/workspace`로 이동해 머리글 "새 문서"를 누르고 `/documents/{id}` URL과 제목 칸을 기다린다. 빠른 실행 카드와 이름이 같아 머리글(`header`) 안에서 찾는다
  2. `write_document`: 제목 칸을 비우고 제목을 입력한다. 본문 편집기를 클릭하고 키보드로 본문을 입력한다. 고정 sleep 없이 `to_have_value`·`to_contain_text`로 확인한다
  3. `save_document`: "저장" 버튼을 누르고 "문서를 저장했어요." 알림을 기다린다
  4. `verify_saved_document`: 페이지를 새로고침하고 제목 칸 값과 본문 글을 확인한다. "임시 저장본을 불러왔어요." 알림이 보이면 서버 저장이 아니라 브라우저 임시 저장본이라는 뜻이므로 실패로 기록한다
- 영향 범위·리스크
  - 기존 시나리오: 문서 목록 조회 단계는 만든 문서가 없으면 지금과 같이 동작한다
  - 실제 사이트에 실행할 때마다 문서가 생긴다(4장)
  - BlockNote 편집기에는 `fill`을 쓸 수 없어 키보드 입력을 쓴다. 본문이 길면 입력 시간이 늘어나므로 본문을 짧게 둔다
  - 본문 입력·저장 단계의 세부 화면 동작은 번들로만 확인했다. 실제 사이트 실행에서 다르면 locator를 고친다
- 공통 모듈 수정: 없음
- 테이블·컬럼 변경: 없음
- 배포 시 주의: 없음

## 6. 결과

### 변경 파일

- `backend/app/automation/locators.py` : 홈 머리글 "새 문서" 버튼, 본문 편집기(`.bn-editor`), "저장" 버튼, 저장 완료·임시 저장본 알림 문구
- `backend/app/automation/steps.py` : 단계 create_document·write_document·save_document·verify_saved_document 추가, `StepContext.created_document_title`, 문서 목록 조회·검색어 입력에서 작성한 문서 우선
- `backend/app/automation/scenarios.py` : `write` 추가, `full`을 17단계 전체 흐름으로 변경
- `backend/tests/fixture_site/index.html` : 가짜 화면에 새 문서 만들기(머리글·빠른 실행 카드), 편집기, 저장·알림, 새로고침 후 유지(localStorage) 추가
- `backend/tests/test_steps_fixture.py` : full 검증 변경, 기존 문서 여정·write·저장 안 한 문서 실패 테스트 추가
- `docs/ai/domain.md` : 용어 "작성한 문서", 대상 문서 우선순위, DOM-005~007
- `README.md` : 시나리오 표에 `write`, `full` 설명 변경, 문서 생성 주의
- `docs/specs/SPEC-20261104-document-write-scenario.md` : 이 명세

### 검증

- 빌드: 백엔드는 빌드 단계 없음. 프론트엔드는 변경 없어 건너뜀(시나리오·단계 목록은 API에서 받음)
- 자동 테스트: `.venv\Scripts\python -m pytest` → 28 passed
- 실행 확인(실제 FixLog, 1회·동시 1)
  - `cli run --scenario write --count 1` → PASSED 15.9초, 문서 `/documents/d99a75c4-…` 생성
  - `cli run --scenario full --count 1` → PASSED 45.8초, 문서 `/documents/f43e48fb-…` 생성, AI 검색 대화방 1개 생성
- 수동 확인 절차: 없음

### 완료 기준 결과

| # | 결과(통과/실패/미확인) | 근거 |
|---|----------------------|------|
| 1 | 통과 | 기본 시나리오 목록에 `write` 추가(자동 테스트 API 시나리오 목록 포함) |
| 2 | 통과 | 실제 사이트 write 실행 7단계 PASSED, 새 문서 만들기 설명에 URL |
| 3 | 통과 | full 실행의 검색 결과 확인에서 작성한 문서 1건, 저장 내용 확인에서 새로고침 후 본문 유지 |
| 4 | 통과 | 실제 사이트 full 실행 17단계 PASSED, 검색 결과 1건 |
| 5 | 미확인 | 대시보드는 코드 변경 없음. 시나리오·단계 목록 API에 포함되는 것은 자동 테스트로 확인, 화면은 열어 보지 않음 |
| 6 | 통과 | pytest 28 passed |

### 명세와 달라진 점

- `write` 시나리오는 작성·저장·확인까지만 하고, 검색·AI 요약까지 이어지는 흐름은 `full`에 넣었다(담당자 지시: 풀 테스트에 모든 흐름)
- 제목 끝에 임의 4자리를 붙였다. 동시 실행 두 개가 같은 초에 문서를 만들면 제목이 같아져 다른 실행의 문서를 열 수 있어서다

### 확인 필요

- 실제 FixLog에 테스트 문서 2개(13:17, 13:18 생성)와 AI 검색 대화방 1개가 생겼다. 필요 없으면 FixLog에서 지운다

### 추가 수정 (2026-11-04)

담당자 지시: 문서 삭제 기능 확인까지 넣는다. 범위는 "휴지통까지만"(영구 삭제·복원 안 함).

- FixLog 화면 분석(번들 `DocumentEditorPage`·`ShareDialog`·`TrashPage`): 문서 머리글 `aria-label="문서 삭제"` 버튼 → alertdialog "삭제하시겠습니까?" → "삭제" 버튼 → 폴더 목록으로 이동. 휴지통 `/trash` 항목에 이름, "문서 · 삭제됨 날짜", "복원"·"영구 삭제" 버튼
- 변경 파일
  - `backend/app/automation/locators.py` : 문서 삭제 버튼, 삭제 확인 창, 휴지통 경로·항목·빈 휴지통 문구
  - `backend/app/automation/steps.py` : 단계 delete_document(작성한 문서인지 제목 확인 → 삭제 → 새로고침 후 검색으로 사라짐 확인), verify_trash(휴지통에 "삭제됨" 항목 확인) 추가
  - `backend/app/automation/scenarios.py` : `write`를 "문서 작성·삭제" 9단계로, `full`에 삭제·휴지통 확인 추가(19단계)
  - `backend/tests/fixture_site/index.html` : 삭제 버튼·확인 창·휴지통 화면, 검색어별 결과 보관(실제 FixLog 동작 재현)
  - `backend/tests/test_steps_fixture.py` : full 테스트에 삭제·휴지통 확인 검증
  - `docs/ai/domain.md` : 작성한 문서 설명, DOM-006 변경, DOM-008 추가
  - `README.md` : `write`·`full` 단계, 데이터 변경 주의
- 구현 중 발견: FixLog 목록 화면은 검색어별 결과를 메모리에 보관한다. full에서 삭제 전에 같은 제목으로 검색했기 때문에 삭제 후 검색에도 삭제한 문서가 계속 보였다(사이드바에서는 사라짐). 검색창을 비우고 다시 입력해도 같았다. 새로고침 후 검색하도록 바꿨고, 가짜 화면에 같은 동작을 넣어 새로고침이 없으면 테스트가 실패하는 것을 확인했다
- 검증
  - 자동 테스트: `.venv\Scripts\python -m pytest` → 28 passed
  - 실제 FixLog(1회·동시 1): `write` PASSED 19.6초(수정 전 로직, 삭제 확인 경로는 full과 같음), `full` PASSED 68.2초(19단계)
  - 실패 실행 2건(13:28, 13:32): 위 화면 동작 때문에 삭제 확인 단계에서 실패. 두 문서 모두 실제로는 삭제되어 휴지통에 있음
- 확인 필요
  - FixLog 쪽 동작: 문서를 삭제한 뒤 목록에서 같은 검색어로 다시 검색하면 삭제한 문서가 보인다. FixLog 버그로 볼지 담당자가 판단한다
  - full 실행 시간이 68초로 늘었다(AI 의미 검색 36초). 기본 시간 제한 120초 안이지만 AI 응답이 느리면 넘을 수 있다. 실행 설정에서 시간 제한을 늘려 실행할 수 있다(상한 600초)
  - 휴지통에 테스트 문서가 쌓인다(오늘 4개: 13:27, 13:28, 13:32, 13:37 생성). 삭제 단계를 넣기 전에 만든 13:17·13:18 문서는 문서 목록에 남아 있다. FixLog에서 직접 지운다

### 추가 수정 2 (2026-11-04)

담당자 지시: full에서 AI 의미 검색을 문서 삭제·휴지통 확인 앞으로 옮기고, AI 검색은 작성한 문서로 확인한다.

- FixLog 화면 분석(번들 `SearchPage`): 답변의 근거 문서는 카드로 표시되며 카드마다 제목(h3), "NN% match", 본문 일부, "문서 열기" 버튼이 있다
- 변경 파일
  - `backend/app/automation/locators.py` : 근거 문서 카드 제목(h3) locator
  - `backend/app/automation/steps.py` : ai_search가 작성한 문서가 있으면 "{제목} 문서를 찾아줘"로 묻고 근거 문서 카드에 그 문서가 없으면 실패. 작성한 문서 경로를 기억해 delete_document가 다른 화면에서도 그 문서로 돌아가 삭제
  - `backend/app/automation/scenarios.py` : full 순서 … 버전 기록 → AI 의미 검색 → 문서 삭제 → 휴지통 확인 → 다른 페이지 이동 → 종료
  - `backend/tests/fixture_site/index.html` : AI 답변에 근거 문서 카드(h3·문서 열기) 표시
  - `backend/tests/test_steps_fixture.py` : full에서 AI 검색이 작성한 문서를 확인하고 삭제·휴지통보다 먼저 실행되는지 검증
  - `docs/ai/domain.md` DOM-005, `README.md` full 설명
- 검증
  - 자동 테스트: pytest 28 passed
  - 실제 FixLog full 2회(13:4x): 둘 다 AI 요약 단계에서 FixLog 응답 "AI 요약에 실패했습니다. 잠시 후 다시 시도해 주세요."로 실패. 기존 문서 대상 `ai` 시나리오도 같은 오류로 실패해 FixLog AI 기능 장애로 판단
  - 실제 FixLog 확인용 실행(AI 요약 제외): 작성 → AI 의미 검색에서 "답변 생성에 실패했습니다"로 실패(같은 장애)
  - 실제 FixLog 확인용 실행(AI 제외): 작성 → 다른 페이지 이동 → 문서 삭제(작성한 문서로 돌아가 삭제) → 휴지통 확인 PASSED
- 확인 필요
  - 미확인: 작성 직후 문서가 FixLog AI 의미 검색 근거에 바로 잡히는지. FixLog AI가 복구된 뒤 full을 다시 실행해 확인해야 한다. 색인이 늦어 근거에 안 나오면 이 단계가 실패하므로 확인 방법을 다시 정한다
  - 실패한 실행 3건의 작성 문서(13:4x 2건, 13:52:02)는 삭제 단계 전에 멈춰 문서 목록에 남아 있다
  - 확인용 실행 2건은 시나리오 ID `check-ai-search-created`로 실행 기록에 남아 대시보드 통계에 포함된다
