# 아키텍처

<!-- 이 문서의 역할: AI가 새 코드를 어디에 두고, 어느 레이어에 무엇을 넣고, 어느 방향으로 호출할지 판단하는 근거다. -->
<!-- 갱신 시점: 모듈 추가, 레이어·폴더 구조 변경, 외부 연동 추가, 버전 업그레이드가 있을 때. -->

## 1. 기술 스택

| 구분 | 이름 | 버전 | 비고 |
|------|------|------|------|
| 언어 | Python / JavaScript(JSX) | 3.15.2 / ES2022 | Python 버전은 `backend/.venv`, 라이브러리 버전은 `backend/requirements.txt`·`frontend/package.json` |
| 프레임워크 | FastAPI / React | 0.162.0 / 19.1.0 | |
| 데이터 접근 | sqlite3 (Python 표준 라이브러리) | Python 내장 | ORM 없음 |
| DB | SQLite | Python 내장 | 로컬 파일, 이 프로그램 전용 |
| 실행 환경 | uvicorn / Playwright | 0.54.0 / 1.64.1 | 브라우저: Playwright Chromium(필요 시 firefox·webkit) |
| 빌드 도구 | pip / npm + Vite | 6.3.5 (Vite) | |
| 화면 | React + react-router-dom | 19.1.0 / 7.6.0 | |
| 자동 테스트 | pytest | 9.2.0 | 대시보드 자동 테스트 없음 |

## 2. 구조 원칙

| ID | 원칙 | 이유 |
|----|------|------|
| ARC-101 | FixLog 화면 문구·aria-label·placeholder·경로는 `backend/app/automation/locators.py`에만 둔다 | FixLog가 배포로 문구를 바꾸면 한 파일만 고치면 된다 |
| ARC-102 | 자동화 동작은 `steps.py`에 단계 함수 하나로 만들어 `STEP_DEFINITIONS`에 등록하고, 앞 단계 결과가 필요하면 `requires`에 선행 단계 ID를 쓴다. 시나리오는 단계 ID 목록으로만 정의한다(`scenarios.py`) | 단계를 여러 시나리오와 대시보드 사용자 정의 시나리오에서 재사용하고, 실패 시 건너뛸 단계를 실행기가 판단한다(DOM-001) |
| ARC-103 | Playwright 실행은 `runner.py`가 만든 별도 스레드 이벤트 루프(`new_playwright_event_loop`)에서만 한다. API 함수에서 브라우저를 직접 띄우지 않는다 | Windows에서 Playwright가 요구하는 Proactor 루프를 보장하고 API 응답을 막지 않는다 |
| ARC-104 | 단계 함수는 화면 조작·검증만 하고, 실패는 `StepFailure`로 던진다. 결과 기록·스크린샷은 `runner.py`가 한다 | 기록 방식이 한 곳에 있어야 모든 단계가 같은 형식으로 남는다 |

## 3. 레이어와 호출 방향

| ID | 규칙 | 이유 |
|----|------|------|
| ARC-001 | 호출은 아래 "레이어별 위치" 표의 위 행에서 아래 행 방향으로만 한다. 레이어를 건너뛰거나 거꾸로 호출하지 않는다 | 건너뛰기·역방향 호출은 트랜잭션과 책임 경계를 깨뜨린다 |
| ARC-002 | 같은 레이어 안의 호출은 "같은 레이어 호출" 칸이 "허용"인 레이어에서만 한다 | 순환 의존을 막는다 |
| ARC-003 | 새 기능의 파일은 "레이어별 위치" 표의 위치와 이름 규칙대로 만든다. 표에 없는 새 최상위 폴더나 새 레이어가 필요하면 만들기 전에 사람에게 묻는다 | 구조가 프로젝트마다·작성자마다 갈라지는 것을 막는다 |

### 레이어별 위치

| 역할 | 이 프로젝트의 이름 | 위치 | 파일 이름 규칙 | 같은 레이어 호출 | 넣지 않는 것 | 예시 파일 |
|------|------------------|------|---------------|---------------|------------|----------|
| 화면 | Page | `frontend/src/pages` | PascalCase.jsx | 금지 | 직접 fetch(api.js 사용) | `frontend/src/pages/History.jsx` |
| 컴포넌트 | 공통 컴포넌트 | `frontend/src/components.jsx` | PascalCase 함수 | 허용 | 서버 호출 | `frontend/src/components.jsx` |
| 상태 관리 | RunSettings Context | `frontend/src/settings.jsx` | use + 이름 훅 | 금지 | 서버 데이터 | `frontend/src/settings.jsx` |
| API 호출 | api 모듈 | `frontend/src/api.js` | `api.동사명사` | 금지 | 화면 상태 | `frontend/src/api.js` |
| 요청 처리 | API 경로 함수 / CLI 명령 | `backend/app/main.py`, `backend/app/cli.py` | `create_app` 안의 함수, `_command_*` | 금지 | 업무 로직(BE-001), 트랜잭션(BE-002) | `backend/app/main.py` |
| 업무 로직 | 실행기·기록 서비스·시나리오 | `backend/app/runner.py`, `backend/app/service.py`, `backend/app/automation/scenarios.py`, `backend/app/automation/auth.py` | `*Runner`, `*Service` 클래스 | 허용 | SQL 문, FixLog 화면 문구(ARC-101) | `backend/app/service.py` |
| 업무 로직 | 자동화 단계 | `backend/app/automation/steps.py` | 단계 ID와 같은 함수명 | 허용 | DB 기록(ARC-104) | `backend/app/automation/steps.py` |
| 업무 로직 | 화면 locator | `backend/app/automation/locators.py` | 대상 이름 함수, `TEXT_`·`LABEL_`·`PLACEHOLDER_` 상수 | 금지 | 대기·검증 로직 | `backend/app/automation/locators.py` |
| 데이터 접근 | repository | `backend/app/repository.py` | `select·insert·update·delete` + 대상 | 금지 | 분기·계산(BE-004), 트랜잭션(BE-002) | `backend/app/repository.py` |
| 쿼리 | 스키마 SQL | `backend/app/schema.sql` | 테이블 소문자 복수형 | 금지 | 데이터 | `backend/app/schema.sql` |

- 데이터 객체(Settings, RunOptions, StepContext, Scenario): `backend/app/config.py`, `backend/app/automation/steps.py`, `backend/app/automation/scenarios.py`, 이름 규칙 PascalCase 명사, 예시 `backend/app/config.py`의 `RunOptions`
- 공통 패키지: 해당 없음. 상태 코드는 `backend/app/constants.py`, 환경 설정은 `backend/app/config.py`, DB 연결·트랜잭션은 `backend/app/db.py`

## 4. 판단 예시

| 이런 코드는 | 여기에 둔다 | 이유 |
|-----------|-----------|------|
| FixLog 화면에서 찾을 문구·버튼 이름 | `locators.py` 상수와 locator 함수 | ARC-101 |
| 새 실행 설정 항목과 그 상한 | `config.py`의 상수 + `RunOptions` Field | API와 CLI가 같은 검증을 쓴다 |
| 실행·단계 상태 코드 | `constants.py`의 `RunStatus`·`StepStatus` | COM-007 |
| 화면이 기대와 다를 때의 처리 | 단계 함수에서 `StepFailure`를 던진다 | ARC-104 |
| 여러 테이블을 함께 바꾸는 저장 | `service.py` 메서드 하나에서 `transaction()` 안에 repository 함수를 호출 | BE-002, BE-003 |

## 5. 대표 요청 흐름

- 대시보드 실행: `Scenarios.jsx` startRun → `api.js#startRun` → `POST /api/runs` (`main.py` post_run) → `BatchRunner.start_batch` → `_run_one` → `steps.py` 단계 함수 → `RunRecordService.record_step`·`finish_run` → `repository.insert_step`·`update_run_finished`
- 실행 이력 조회: `History.jsx` → `api.js#getRuns` → `GET /api/runs` → `RunRecordService.get_run_list` → `repository.select_run_list`

## 6. 모듈 목록

| 모듈(업무) | 패키지/폴더 | 설명 |
|-----------|------------|------|
| 브라우저 자동화 | `backend/app/automation` | locator, 단계, 시나리오, 사람 보조 로그인 |
| 실행·기록 | `backend/app/runner.py`, `backend/app/service.py`, `backend/app/repository.py` | 반복·동시 실행·시간 제한, 결과 저장·조회 |
| API·CLI | `backend/app/main.py`, `backend/app/cli.py` | 대시보드 API, 명령줄 실행 |
| 대시보드 | `frontend/src` | 대시보드·시나리오·실행 설정·실행 이력·실행 상세 화면 |

## 7. 외부 연동

| 대상 시스템 | 방식(API/DB링크/파일/MQ) | 구현 위치(클래스·설정 파일) | 주의사항 |
|------------|------------------------|--------------------------|---------|
| FixLog 프론트엔드(외부 서비스) | 실제 브라우저(Playwright) | `.env`의 `FIXLOG_BASE_URL`, `backend/app/automation/locators.py` | 실제 서비스다. BAN-101·BAN-102, PRJ-004·PRJ-005. FixLog API(https://fixlog.art/fixlog)를 HTTP로 직접 호출하지 않는다 |
| Google OAuth | 브라우저 로그인(사람 보조) | `backend/app/automation/auth.py` | BAN-103. 무인 실행에서는 저장된 로그인 상태만 쓴다 |

## 8. 환경과 설정

| 환경 | 용도 | 설정 파일 | AI 접근 |
|------|------|----------|--------|
| 로컬 | 개발·실행 | 저장소 최상위 `.env`(예시 `.env.example`), `backend/app/config.py` | 허용(`.env` 내용 출력 금지, BAN-104) |
| 개발 서버 | 해당 없음 | 해당 없음 | 해당 없음 |
| FixLog 실서비스(외부) | 자동화 대상 | `.env`의 `FIXLOG_BASE_URL` | 이 프로그램의 브라우저 자동화로만 허용(BAN-002, BAN-101, PRJ-005) |
