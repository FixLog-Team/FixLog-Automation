# 코딩 컨벤션

<!-- 이 문서의 역할: 이름 규칙, 코드 형식, 언어별 작성 규칙이다. 파일 전체를 프로젝트가 채운다. -->
<!-- 적용 범위: 새 파일과 새로 작성하는 코드. 기존 파일은 그 파일의 기존 스타일을 따른다(COM-002). 기존 코드를 이 문서에 맞춰 일괄 정리하지 않는다(BAN-004). -->
<!-- 언어: Python(2장), JavaScript(3장). SQL 이름 규칙은 sql.md 2장. -->

## 1. 공통

| 항목 | 값 |
|------|----|
| 업무 용어 이름 | domain.md "용어집"의 코드 이름(약어)을 쓴다 |
| 자동 포맷터·린터 | 없음 |
| 설정 파일 위치 | 해당 없음 |

<!-- 자동 포맷터·린터 설정이 있으면 그 설정이 이 문서보다 우선한다. 이 문서에는 도구로 강제하지 않는 내용만 쓴다. -->

### 1.1 공통 작성 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| CONV-001 | 불리언 변수·함수 이름은 is·has·can·should로 시작한다 | 값이 참/거짓인지 이름만으로 알 수 있다 |
| CONV-002 | 의미 있는 숫자·문자열(대기 시간, 상한, 경로, 저장소 키, 화면 문구)은 이름 있는 상수로 만들고 한 곳에서만 정의한다 | 같은 값이 여러 곳에 있으면 한쪽만 고쳐진다 |
| CONV-003 | 삼항 연산자를 중첩하지 않는다. 경우가 3개 이상이면 분기문이나 값 매핑 객체를 쓴다 | 중첩 삼항은 조건 순서를 잘못 읽기 쉽다 |
| CONV-004 | data, result, info, item, flag처럼 무엇인지 알 수 없는 이름을 쓰지 않는다 | 이름으로 담긴 값을 알 수 있어야 한다 |
| CONV-005 | 조회 함수(get·select·find)는 조회만 한다. 저장·화면 이동·알림을 넣지 않는다 | 이름에 드러나지 않는 부수 효과는 호출하는 쪽이 예상하지 못한다 |

## 2. 언어별 컨벤션: Python

- 기반 스타일 가이드: PEP 8
- 적용 파일: `backend/**/*.py`

### 2.1 이름 규칙

| 대상 | 규칙 | 예 |
|------|------|----|
| 패키지·네임스페이스·폴더 | 소문자, 역할 이름 | `app.automation` |
| 클래스·타입 | PascalCase, 역할 접미사(Runner, Service, Error) | `BatchRunner`, `RunRecordService` |
| 메서드·함수 | snake_case, 동사로 시작. 자동화 단계 함수는 단계 ID와 같게 | `create_batch`, `open_document` |
| 변수·파라미터 | snake_case | `run_id` |
| 상수 | 대문자 스네이크 | `MAX_CONCURRENCY` |
| 파일 | snake_case, 모듈 역할 이름 | `runner.py` |
| 테스트 | `test_` + 대상 모듈, 함수는 `test_` + 기대 동작 | `test_api.py`, `test_run_request_over_limit_is_rejected` |

| 동작 | 동사 | 예 |
|------|------|----|
| 목록 조회 | repository `select_..._list`, service `get_..._list` | `select_run_list`, `get_run_list` |
| 단건 조회 | repository `select_...`, service `get_...` | `select_run`, `get_run` |
| 등록 | repository `insert_...`, service `create_...`·`add_...`·`record_...` | `insert_step`, `record_step` |
| 수정 | repository `update_...`, service `start_...`·`finish_...` | `update_run_finished`, `finish_run` |
| 삭제 | repository `delete_...`, service `remove_...` | `delete_custom_scenario`, `remove_custom_scenario` |

### 2.2 형식

| 항목 | 값 |
|------|----|
| 들여쓰기 | 공백 4칸 |
| 한 줄 최대 길이 | 120자 |

<!-- 이 표에 없는 형식(중괄호 위치, 따옴표, import 순서)은 architecture.md "레이어별 위치" 표의 예시 파일을 따른다. -->

### 2.3 작성 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| CONV-006 | 함수 인자와 반환값에 타입 힌트를 쓴다 | 레이어 사이에 오가는 값의 형태를 코드로 알 수 있다 |
| CONV-007 | Playwright는 비동기 API(`playwright.async_api`)만 쓴다 | 동시 실행을 한 이벤트 루프에서 처리한다 (ARC-103) |
| CONV-008 | 로그는 모듈마다 `logging.getLogger(__name__)`로 만든 로거를 쓴다. CLI 결과 출력만 `sys.stdout.write`를 쓴다 | COM-020 |

## 3. 언어별 컨벤션: JavaScript (React)

- 기반 스타일 가이드: 없음
- 적용 파일: `frontend/src/**/*.js`, `frontend/src/**/*.jsx`

### 3.1 이름 규칙

| 대상 | 규칙 | 예 |
|------|------|----|
| 패키지·네임스페이스·폴더 | 소문자 | `src/pages` |
| 메서드·함수 | camelCase, 동사로 시작 | `startRun`, `formatDuration` |
| 변수·파라미터 | camelCase | `runId` |
| 상수 | 대문자 스네이크 | `POLL_INTERVAL_MS` |
| 컴포넌트 | PascalCase, 페이지는 파일명과 같게 | `RunDetail.jsx` |
| 파일 | 컴포넌트 파일은 PascalCase.jsx, 그 밖은 camelCase.js | `api.js`, `History.jsx` |
| 테스트 | 해당 없음(대시보드 자동 테스트 없음) | |

| 동작 | 동사 | 예 |
|------|------|----|
| 목록 조회 | `get...s` | `api.getRuns` |
| 단건 조회 | `get...` | `api.getRun` |
| 등록 | `create...`, `start...` | `api.createScenario`, `api.startRun` |
| 수정 | 해당 없음 | |
| 삭제 | `delete...` | `api.deleteScenario` |

### 3.2 형식

| 항목 | 값 |
|------|----|
| 들여쓰기 | 공백 2칸 |
| 한 줄 최대 길이 | 120자 |

### 3.3 작성 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| CONV-009 | `var`를 쓰지 않고 `const`·`let`을 쓴다 | 블록 범위가 아닌 변수는 의도하지 않은 재할당을 만든다 |
| CONV-010 | 같은 비교 기준은 `===`·`!==`만 쓴다 | 암묵적 형변환 비교는 예상과 다른 결과를 낸다 |
