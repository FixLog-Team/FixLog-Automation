# 업무 도메인

<!-- 이 문서의 역할: AI가 업무 용어, 코드값, 업무 규칙, 테이블 의미를 확인하는 곳이다. 파일 전체를 프로젝트가 채운다. -->
<!-- 갱신 시점: 용어·공통코드·업무 규칙이 추가·변경될 때. -->

## 1. 업무 개요

FixLog는 문서 목록·제목 검색·AI 의미 검색·AI 요약·버전 기록을 제공하는 외부 문서 서비스다(Google 로그인).
이 프로그램은 FixLog 담당자가 테스트 계정으로 FixLog 사용자 여정을 자동 실행해 정상 동작을 확인하는 데 쓴다.
담당자는 대시보드에서 시나리오와 실행 설정을 고르고 실행 이력·실패 화면을 본다.
FixLog 화면 분석 결과와 locator 근거는 `docs/specs/SPEC-20261104-fixlog-browser-automation.md` 2장에 있다.

## 2. 용어집

| 용어 | 코드 이름(약어) | 정의 | 혼동 주의 |
|------|---------------|------|----------|
| 실행 요청 | batch | 한 번의 실행 버튼(또는 `cli run`)으로 만든 실행 묶음. 실행 횟수만큼 run을 가진다 | 동시에 하나만 실행할 수 있다 |
| 실행 | run | 시나리오를 브라우저 하나로 처음부터 끝까지 한 번 실행한 것 | 회차는 `iteration` |
| 단계 | step | 시나리오를 이루는 자동화 동작 하나(예: 문서 상세 진입) | `seq` 0은 항상 "브라우저 실행" |
| 시나리오 | scenario | 단계 ID의 순서 목록 | 기본 시나리오는 코드(`scenarios.py`), 사용자 정의는 DB |
| 인증 상태 | auth state | Playwright `storage_state` 파일. FixLog localStorage의 `access_token`·`refresh_token` 포함 | Google 계정 비밀번호와 다르다 |
| 대상 문서 | target document | AI 요약·버전 기록·검색에 쓰는 문서 | 우선순위: 이 실행에서 작성한 문서 → `TEST_DOCUMENT_TITLE` → 문서 목록 첫 문서 |
| 작성한 문서 | created document | 문서 작성 단계가 이 실행에서 만든 문서. 제목 `자동화 테스트 문서 YYYY-MM-DD HH:MM:SS xxxx` | 문서 삭제 단계를 거치면 FixLog 휴지통에 남는다 |
| 제목 검색 | title search | FixLog `/documents`의 "제목으로 검색..." 입력 | AI 의미 검색(`/search`)과 다르다. 제목 검색은 데이터를 바꾸지 않는다 |
| AI 의미 검색 | ai search | FixLog 홈·`/search`의 자연어 질문 | FixLog 서버에 대화방이 생긴다 |

## 3. 공통코드

- 공통코드 테이블: 해당 없음 (코드값은 `backend/app/constants.py`)

| 코드 그룹 | 코드값 | 의미 | 사용처 |
|----------|-------|------|-------|
| RunStatus | QUEUED | 실행 대기 | runs.status, batches.status |
| RunStatus | RUNNING | 실행 중 | runs.status, batches.status |
| RunStatus | PASSED | 모든 단계 성공 | runs.status, batches.status |
| RunStatus | FAILED | 한 단계 이상 실패 | runs.status, batches.status |
| StepStatus | PASSED / FAILED / SKIPPED | 단계 성공 / 실패 / 앞 단계 실패로 건너뜀 | run_steps.status |

## 4. 핵심 업무 흐름

| 업무 | 상태 흐름 | 상태 변경 주체 |
|------|----------|--------------|
| 실행 | QUEUED → RUNNING → PASSED 또는 FAILED | 실행기(`runner.py`). 서버 재시작 시 남은 QUEUED·RUNNING은 FAILED로 정리 |
| 실행 요청 | RUNNING → PASSED(모든 run 성공) 또는 FAILED | 실행기 |

## 5. 업무 규칙

| ID | 규칙 | 근거 |
|----|------|------|
| DOM-001 | 단계가 실패해도 기록하고 다음 단계를 실행한다. 선행 단계(`StepDefinition.requires`)가 이 실행에서 실패·건너뜀이면 SKIPPED("'선행 단계' 실패로 실행하지 않음"). 브라우저 실행 실패·시간 초과, 또는 `stop_on_failure`면 뒤 단계를 모두 SKIPPED로 하고 "브라우저 종료"만 실행한다. `runs.failed_step`은 처음 실패한 단계 | SPEC-20261104-continue-on-failure, 담당자 승인 |
| DOM-002 | 실패한 단계는 스크린샷을 항상 저장한다. 성공 단계는 `save_success_screenshots`일 때만 저장한다 | 담당자 요구(실패 화면 확인) |
| DOM-003 | 실행 시간 제한을 넘으면 그 시점의 단계를 실패로 기록한다 | 명세 2장 실행 설정 |
| DOM-004 | FixLog "요약" 버튼은 요약 전에 문서를 저장한다. AI 요약 단계는 대상 문서에 버전 기록을 만들 수 있다 | FixLog 번들 분석(2026-11-04), 담당자 승인 |
| DOM-005 | 문서 작성 단계를 실행한 실행에서는 작성한 문서를 대상 문서로 쓰고, 검색어는 작성한 문서 제목 전체로 한다. AI 의미 검색은 "{제목} 문서를 찾아줘"로 묻고 답변 근거 문서 카드에 작성한 문서가 있어야 성공이다 | SPEC-20261104-document-write-scenario |
| DOM-006 | 문서 삭제 단계는 이 실행에서 작성한 문서만 삭제(휴지통 이동)한다. 열린 문서 제목이 작성한 문서와 다르면 삭제하지 않고 실패로 기록한다. 휴지통의 영구 삭제·복원은 하지 않는다 | 담당자 승인(2026-11-04, 휴지통까지만) |
| DOM-008 | 삭제 후 목록 확인은 새로고침 뒤에 검색한다 | FixLog 목록 화면은 검색어별 결과를 메모리에 보관해, 삭제 전에 같은 검색어로 검색했으면 삭제 뒤에도 옛 결과를 보여 준다 |
| DOM-007 | 저장 내용 확인은 새로고침 후 제목·본문을 본다. "임시 저장본을 불러왔어요." 알림이 보이면 서버 저장 실패로 기록한다 | FixLog는 저장하지 않은 변경을 브라우저 localStorage에 임시 저장한다 |

## 6. 주요 테이블

| 테이블 | 업무 의미 | 기본 키 | 비고 |
|--------|----------|--------|------|
| batches | 실행 요청 | id | options_json에 요청 설정(RunOptions) JSON |
| runs | 실행 | id | failed_step에는 단계 ID가 아니라 단계 이름(한글)이 들어 있다 |
| run_steps | 단계 결과 | id | screenshot_path는 `DATA_DIR/screenshots` 기준 상대 경로 |
| custom_scenarios | 사용자 정의 시나리오 | id(`custom-` + 8자리) | steps_json에 단계 ID 배열 |
