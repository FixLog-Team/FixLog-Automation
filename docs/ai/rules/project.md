# 프로젝트 규칙

<!-- 이 문서의 역할: 공통 모듈, 수정 금지·주의 영역, 특정 레이어에 속하지 않는 이 프로젝트 규칙을 쓴다. -->

## 1. 공통 모듈

| 모듈 | 위치 | 설명 |
|------|------|------|
| 환경 설정·실행 상한 | `backend/app/config.py` | `Settings`, `RunOptions`, 상한 상수. API·CLI·실행기가 함께 쓴다 |
| DB 연결·트랜잭션 | `backend/app/db.py` | `connect`, `transaction`, `init_db` |
| 상태 코드 | `backend/app/constants.py` | `RunStatus`, `StepStatus` |
| 실행 기록 서비스 | `backend/app/service.py` | `RunRecordService`. 실행기·API·CLI가 함께 쓴다 |
| FixLog locator | `backend/app/automation/locators.py` | 모든 단계와 로그인이 쓰는 화면 문구·locator |
| 대시보드 API 호출·조회 훅 | `frontend/src/api.js`, `frontend/src/hooks.js` | 모든 화면이 쓰는 서버 호출과 `useServerData` |

## 2. 수정 금지·주의 영역

| 경로 | 구분(금지/승인 필요) | 이유 |
|------|-------------------|------|
| `backend/.auth/` | 금지 | 사람이 `python -m app.cli auth`로 만든 로그인 토큰이다 (BAN-104) |
| `backend/data/` | 금지 | 실행 결과 DB·스크린샷. 프로그램만 쓴다 |
| `frontend/dist/`, `frontend/node_modules/`, `backend/.venv/` | 금지 | 빌드·설치 결과물이다. 명령으로 다시 만든다 |
| `backend/app/schema.sql` | 승인 필요 | 기존 실행 기록 DB와 호환이 깨진다 (WF-004) |
| `backend/tests/fixture_site/index.html` | 승인 필요 | 실제 FixLog 화면을 흉내 낸 기준이다. PRJ-002일 때만 함께 바꾼다 |

## 3. 프로젝트 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| PRJ-001 | `locators.py`의 화면 문구를 바꿀 때는 실제 FixLog 화면이나 배포 번들(`/assets/*.js`)에서 문구를 확인한 뒤 바꾸고, 확인한 날짜를 파일 머리 주석에 고친다 | 추측한 locator는 실제 화면에서 실패한다(담당자 요구: 화면 구조를 추측해 구현하지 않는다) |
| PRJ-002 | `locators.py`의 문구나 화면 구조 가정을 바꾸면 `backend/tests/fixture_site/index.html`도 같은 문구·구조로 바꾼다 | 가짜 화면이 실제 화면과 달라지면 자동 테스트가 통과해도 실제 실행이 실패한다 |
| PRJ-003 | 화면 대기는 locator 상태 기반(`expect`, `wait_for`, `wait_for_url`)으로 한다. 고정 대기(`asyncio.sleep`, `wait_for_timeout`)는 `runner.py`의 사용자 설정 대기(`step_delay_ms`, `interval_sec`)에만 쓴다 | 고정 대기는 느린 응답에서 실패하고 빠른 응답에서 시간을 낭비한다 |
| PRJ-004 | FixLog 데이터를 바꾸는 버튼(복원·삭제·영구 삭제·공유·이동·태그 추가·저장)을 누르는 단계를 담당자 승인 없이 추가하지 않는다. 승인된 변경: AI 요약의 자동 저장, AI 의미 검색의 대화방 생성, 이 실행에서 작성한 문서의 생성·저장·삭제(휴지통 이동, DOM-006) | 테스트 계정 데이터라도 되돌리기 어려운 변경은 사람이 정한다 |
| PRJ-005 | AI가 검증을 위해 실제 FixLog에 시나리오를 실행할 때는 실행 횟수 1, 동시 실행 수 1로만 한다 | 검증 목적의 실행이 실제 서비스 부하·분석 데이터를 늘리지 않게 한다 |
| PRJ-006 | 실제 FixLog 대상 로그인 이후 단계 검증은 담당자가 `python -m app.cli auth`를 실행한 뒤에만 한다. AI가 Google 계정 정보를 입력하지 않는다 | 테스트 계정 인증은 사람이 직접 한다 (BAN-103, BAN-104) |
