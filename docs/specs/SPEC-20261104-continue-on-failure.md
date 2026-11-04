# SPEC-20261104-continue-on-failure 실패해도 다음 단계 계속

| 항목 | 값 |
|------|----|
| 상태 | 확정 |
| 담당자 | 프로젝트 담당자 |
| 유형 | 수정 |

## 1. 목적

한 단계가 실패해도 실패를 기록하고 다음 단계를 계속 실행해, 한 번의 실행으로 FixLog 기능별 상태를 모두 확인한다.
중간 실패로 문서 삭제 단계까지 가지 못해 테스트 문서가 남는 문제도 함께 줄인다.

## 2. 요구 사항

- 대상 화면·기능: 실행기(`backend/app/runner.py`), 단계 정의(`steps.py`), 실행 설정(API `POST /api/runs`, CLI `run`, 대시보드 "실행 설정" 화면)
- 현재: 한 단계가 실패하면 뒤의 단계는 모두 SKIPPED이고 "브라우저 종료"만 실행한다(DOM-001). 2026-11-04 FixLog AI 장애 때 AI 요약 실패로 버전 기록·문서 삭제·휴지통 확인을 확인하지 못했고 테스트 문서가 남았다
- 변경 후
  - 실행 설정 "실패해도 다음 단계 계속"(`stop_on_failure` 반대 의미). 기본값: 계속한다
    - API·CLI 필드 `stop_on_failure`(기본 false). CLI 옵션 `--stop-on-failure`
    - 대시보드 실행 설정 화면에 체크박스 "첫 실패에서 멈춤"(기본 해제)
  - 계속 모드
    - 단계가 실패하면 실패·스크린샷을 기록하고 다음 단계를 실행한다
    - 단계마다 선행 단계를 정한다. 선행 단계가 이 실행에서 실패하거나 건너뛰어졌으면 그 단계는 SKIPPED로 기록하고 설명에 "'선행 단계 이름' 실패로 실행하지 않음"을 쓴다. 선행 단계가 시나리오에 없으면 실행한다(단계 안의 기존 확인이 처리)
    - 선행 단계 표
      | 단계 | 선행 단계 |
      |------|----------|
      | 사이트 접속, 로그인 페이지 확인, 로그인 | 없음 |
      | 워크스페이스 진입, 문서 목록 조회, 검색어 입력, 문서 상세 진입, 다른 페이지 이동, AI 의미 검색, 새 문서 만들기 | 로그인 |
      | 검색 결과 확인 | 검색어 입력 |
      | AI 요약 실행, 버전 기록 조회 | 문서 상세 진입 |
      | 문서 작성 | 새 문서 만들기 |
      | 문서 저장, 문서 삭제 | 문서 작성 |
      | 저장 내용 확인 | 문서 저장 |
      | 휴지통 확인 | 문서 삭제 |
    - 브라우저 실행 실패, 실행 시간 제한 초과는 계속할 수 없으므로 그 뒤 단계를 모두 SKIPPED로 한다(브라우저 종료 제외)
  - 멈춤 모드(`stop_on_failure=true`): 지금과 같다
  - 공통: 실패 단계가 하나라도 있으면 실행 결과는 FAILED. `runs.failed_step`·`error_message`는 처음 실패한 단계
- 범위 밖
  - 실패한 단계 재시도
  - 실행 이력 화면에 실패 단계 여러 개 표시(상세 화면 단계 목록에서는 모두 보임)
  - 후속 과제: 서버 시작 시 다른 터미널에서 진행 중인 CLI 실행을 실패로 바꾸는 문제

## 3. 완료 기준

- 전제: 가짜 FixLog 화면(자동 테스트). 실제 사이트는 1회·동시 1(PRJ-005)

| # | 입력·동작 | 기대 결과 |
|---|----------|----------|
| 1 | 기본 설정으로 AI 요약이 실패하는 시나리오 실행 | AI 요약 FAILED, 뒤의 버전 기록 등은 실행(PASSED/FAILED), 실행 결과 FAILED, failed_step "AI 요약 실행" |
| 2 | 기본 설정으로 문서 작성이 실패하는 시나리오 실행 | 문서 저장·저장 내용 확인·문서 삭제·휴지통 확인 SKIPPED("'문서 작성' 실패로 실행하지 않음"), 관계없는 단계는 실행 |
| 3 | `stop_on_failure=true` | 지금처럼 첫 실패 뒤 모두 SKIPPED, 브라우저 종료만 실행 |
| 4 | 대시보드 실행 설정 | "첫 실패에서 멈춤" 체크박스가 있고 실행 요청에 반영된다 |
| 5 | `cli run --stop-on-failure` | 3번과 같은 동작 |
| 6 | `pytest`, `npm run build` | 모두 성공 |

## 4. 미결 사항

- 없음 (기본값 "계속"은 담당자 승인, 2026-11-04)

## 5. 구현 계획

### 5.1 수정 파일

| 파일 | 구분(신규/수정/삭제/이름 변경) | 변경 내용 |
|------|------------------------------|----------|
| `backend/app/config.py` | 수정 | `RunOptions.stop_on_failure: bool = False` |
| `backend/app/automation/steps.py` | 수정 | `StepDefinition.requires`와 선행 단계 지정 |
| `backend/app/runner.py` | 수정 | 계속 모드, 선행 단계 실패 시 SKIPPED, 브라우저 실행 실패·시간 초과 시 중단 |
| `backend/app/cli.py` | 수정 | `--stop-on-failure` |
| `frontend/src/settings.jsx` | 수정 | 기본값·요청 변환에 `stop_on_failure` |
| `frontend/src/pages/RunSettings.jsx` | 수정 | "첫 실패에서 멈춤" 체크박스 |
| `backend/tests/test_steps_fixture.py` | 수정 | 계속 모드·선행 단계·멈춤 모드 테스트 |
| `docs/ai/domain.md` | 수정 | DOM-001 변경 |
| `README.md` | 수정 | 실행 설정·CLI 옵션 |
| `docs/specs/SPEC-20261104-continue-on-failure.md` | 신규 | 이 명세 |

### 5.2 처리 방식·영향 범위

- 참고 코드: `runner.py` `_run_one`의 단계 반복
- 처리 순서
  1. 단계 결과를 `{step_id: status}`로 모은다
  2. 단계마다 멈춤 조건(멈춤 모드에서 실패 있음, 브라우저 실행 실패, 시간 초과)이면 SKIPPED
  3. 아니면 `requires` 중 이 실행에서 FAILED·SKIPPED인 단계가 있으면 SKIPPED(이유에 그 단계 이름)
  4. 그 외에는 실행
- 영향 범위·리스크
  - 기본 동작이 바뀐다. 실패 뒤에도 FixLog에 요청을 계속 보내므로 실행 시간 제한(기존 상한)이 그대로 적용된다
  - 실패한 단계가 열어 둔 대화상자·패널이 다음 단계를 막을 수 있다. 다음 단계는 자기 화면으로 이동하거나 기존처럼 대화상자를 닫고 시작한다
  - 저장된 이전 실행 기록(options_json)에는 이 필드가 없다. 조회에는 영향이 없다
- 공통 모듈 수정: 없음
- 테이블·컬럼 변경: 없음
- 배포 시 주의: 프론트엔드 다시 빌드(`npm run build`)

## 6. 결과

### 변경 파일

- `backend/app/config.py` : `RunOptions.stop_on_failure`(기본 false)
- `backend/app/automation/steps.py` : `StepDefinition.requires`, 2장 표대로 선행 단계 지정
- `backend/app/runner.py` : 단계 결과 모음, `_skip_reason`(종료 단계 제외 → 중단 사유 → 멈춤 모드 → 선행 단계), 시간 초과 시 중단, 건너뜀 사유 기록
- `backend/app/cli.py` : `--stop-on-failure`
- `frontend/src/settings.jsx` : 기본값·요청 변환에 `stop_on_failure`
- `frontend/src/pages/RunSettings.jsx` : "첫 실패에서 멈춤" 체크박스
- `backend/tests/test_steps_fixture.py` : 기존 건너뜀 테스트를 멈춤 모드로 변경, 계속 모드·선행 단계 건너뜀 테스트 추가
- `docs/ai/domain.md` : DOM-001 변경
- `README.md` : CLI 예시, 실패 시 동작 설명
- `docs/specs/SPEC-20261104-continue-on-failure.md` : 이 명세

### 검증

- 빌드: `cd frontend && npm run build` 성공
- 자동 테스트: `.venv\Scripts\python -m pytest` → 30 passed
- 실행 확인: 실제 FixLog `cli run --scenario full --count 1`(FixLog AI 장애 중) → AI 요약·AI 의미 검색 FAILED, 버전 기록·문서 삭제·휴지통 확인·다른 페이지 이동 PASSED, 실행 FAILED, 109.0초
- `cli run --help`에 `--stop-on-failure` 표시 확인
- 수동 확인 절차(완료 기준 4): 서버 실행 → http://127.0.0.1:8000/settings → "첫 실패에서 멈춤" 체크 → 시나리오 화면에서 실행 → 실행 상세에서 첫 실패 뒤 단계가 모두 "앞 단계 실패로 실행하지 않음"인지 확인

### 완료 기준 결과

| # | 결과(통과/실패/미확인) | 근거 |
|---|----------------------|------|
| 1 | 통과 | 자동 테스트 계속 모드 테스트, 실제 사이트 full 실행 |
| 2 | 통과 | 자동 테스트 선행 단계 건너뜀(사유 문구 포함) |
| 3 | 통과 | 자동 테스트 멈춤 모드 |
| 4 | 미확인 | 빌드 성공. 화면은 열어 보지 않음(서버를 띄우면 다른 터미널의 진행 중 실행을 실패로 바꾸는 문제가 있어 띄우지 않음). 수동 확인 절차 참고 |
| 5 | 미확인 | CLI 인자가 RunOptions로 전달되는 것은 코드로 확인, 실제 실행은 안 함 |
| 6 | 통과 | pytest 30 passed, npm run build 성공 |

### 명세와 달라진 점

- 없음

### 확인 필요

- 실패가 있으면 실행 시간이 늘어난다. FixLog AI 장애 때 AI 요약·AI 검색이 각각 약 40초 걸린 뒤 실패해 full이 109초였다(기본 시간 제한 120초). 시간 제한에 걸리면 뒤 단계(문서 삭제 포함)가 건너뛰어지므로 기본 시간 제한을 180초로 올릴지 정한다(상한 600초는 그대로)

### 추가 수정 (2026-11-04)

- 담당자 결정: 기본 실행 시간 제한을 120초에서 180초로 올린다(상한 600초는 그대로)
- 변경 파일: `backend/app/config.py` `DEFAULT_RUN_TIMEOUT_SEC`, `frontend/src/settings.jsx` 기본값, `README.md` 7장
- 위 "확인 필요"의 시간 제한 항목은 해결됨. 대시보드에 이미 저장된 실행 설정(브라우저 localStorage)은 예전 값 120초를 그대로 쓴다
