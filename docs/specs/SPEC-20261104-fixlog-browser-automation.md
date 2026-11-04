# SPEC-20261104-fixlog-browser-automation FixLog 브라우저 자동화 프로그램

| 항목 | 값 |
|------|----|
| 상태 | 확정 |
| 담당자 | |
| 유형 | 신규 |

## 1. 목적

FixLog(https://fix-log-front-theta.vercel.app)에 실제 Chromium 브라우저(Playwright)로 접속해 사용자 여정(로그인 → 문서 목록 → 검색 → 문서 상세 → AI 요약 → 버전 기록)을 자동 실행하고, 단계별 성공/실패·스크린샷·소요 시간을 기록해 React 대시보드에서 확인하는 독립 프로그램을 만든다. FixLog 원본 프로젝트는 수정하지 않는다.

## 2. 요구 사항

- 대상 화면·기능: FixLog 프론트엔드 `/login`, `/login/callback`, `/workspace`, `/documents`, `/documents/:documentId`, `/search`
- 현재: 없음(신규)
- 변경 후:
  - **사이트 분석 결과(2026-11-04, 배포 번들 `assets/index-CznndP-r.js` 및 lazy chunk 소스 기준)**
    - 앱 구조: Vite + React SPA, React Router. API 서버는 `https://fixlog.art/fixlog`
    - 인증: `/login`의 "Continue with Google" 버튼 → 백엔드 `/login?redirect_uri=.../login/callback` → Google OAuth → `/login/callback?accessToken=...&refreshToken=...` → 토큰을 **localStorage**(`access_token`, `refresh_token`, `workspace_id`)에 저장 → `/workspace`로 이동
    - 보호 라우트: `/workspace`, `/documents`, `/documents/:id`, `/search`, `/trash`, `/settings`는 토큰이 없으면 `/login`으로 리다이렉트. **`/documents`는 비로그인 데모가 아니라 로그인 필요 화면이다**
    - 비로그인 접근 가능: `/`(랜딩), `/login`, `/privacy`
  - **Locator 설계(분석한 실제 텍스트·속성 기준)**

    | 대상 | 화면 | Locator |
    |------|------|---------|
    | Google 로그인 버튼 | `/login` | `get_by_role("button", name="Continue with Google")` |
    | 로그인 처리 중 | `/login/callback` | `get_by_text("로그인 처리 중...")` 사라짐 + URL `**/workspace` |
    | 워크스페이스 홈 진입 확인 | `/workspace` | `get_by_role("heading", name="무엇을 찾고 계신가요?")` 또는 `get_by_text("최근 문서")` |
    | AI 검색 입력(홈) | `/workspace` | `get_by_placeholder("FixLog에게 필요한 문서를 찾아달라고 해보세요...")` |
    | 문서 목록 제목 검색 | `/documents` | `get_by_placeholder("제목으로 검색...")` (입력 후 300ms 디바운스 → API 조회) |
    | 문서 행 | `/documents` | `role="button"` 행 안의 제목 텍스트. `get_by_role("button").filter(has_text=<제목>)` |
    | 검색 결과 없음 | `/documents` | `get_by_text("검색 결과가 없습니다.")` |
    | 로딩 표시 | 공통 | `get_by_text("불러오는 중…")` 사라짐 대기 |
    | 문서 상세 진입 확인 | `/documents/:id` | `get_by_label("문서 제목")`(제목 input), `get_by_text("문서를 불러오는 중…")` 사라짐 |
    | 문서 접근 오류 | `/documents/:id` | `get_by_text("문서에 접근할 권한이 없습니다.")`, `get_by_text("문서를 불러오지 못했습니다.")` |
    | AI 요약 버튼 | 상세 헤더 | `get_by_role("button", name="요약", exact=True)` |
    | AI 요약 패널 | 상세 우측 | `get_by_role("complementary").filter(has_text="문서 AI")` |
    | 요약 진행/결과 | AI 패널 | 진행: `"요약하는 중…"`, 실패: `"AI 요약에 실패했습니다. 잠시 후 다시 시도해 주세요."`, 빈 결과: `"요약 결과가 비어 있습니다."`, 그 외 = 성공(본문 텍스트 존재) |
    | 버전 기록 버튼 | 상세 헤더 | `get_by_role("button", name="버전 기록")` (aria-label) |
    | 버전 기록 패널 | 상세 우측 | `get_by_role("complementary").filter(has_text="버전 기록")` |
    | 버전 항목 | 버전 패널 | `listitem` 안의 button, 텍스트 `v{번호}`. 없음: `"아직 이전 버전이 없습니다."`, 오류: `"버전 기록을 불러오지 못했습니다."` |
    | 이전 버전 미리보기 | 상세 본문 | `get_by_text("버전을 보고 있어요 · 읽기 전용")`, 되돌아가기 `get_by_role("button", name="현재 버전으로 돌아가기")` |
    | 패널 닫기 | 우측 패널 | `get_by_role("button", name="패널 닫기")` |

    - 클래스명(Tailwind)이나 번들 내부 이름은 배포마다 바뀌므로 사용하지 않는다. role·aria-label·placeholder·화면 문구만 쓴다
    - 화면 문구가 바뀌면 locator를 한 파일(`automation/locators.py`)에서만 고치도록 모은다
  - **브라우저 자동화 단계(개별 실행 가능)**: 1 사이트 접속, 2 로그인 페이지 확인, 3 로그인(저장된 인증 상태 사용), 4 워크스페이스 진입, 5 문서 목록 조회, 6 검색어 입력, 7 검색 결과 확인, 8 문서 상세 진입, 9 AI 요약 실행, 10 버전 기록 조회, 11 다른 페이지 이동, 12 브라우저 종료
  - **시나리오**: 단계를 순서대로 묶은 정의. 기본 4종(기본 탐색 / 검색 / AI 기능 / 버전 관리)을 제공하고, 대시보드에서 단계를 골라 사용자 정의 시나리오를 저장할 수 있다
  - **실행 설정과 상한**

    | 항목 | 기본값 | 상한 |
    |------|-------|------|
    | 브라우저 종류 | chromium | chromium / firefox / webkit |
    | 실행 모드 | headless | headless / headed |
    | 실행 횟수 | 1 | 20 |
    | 동시 실행 수 | 1 | 3 |
    | 단계 사이 대기(사람과 비슷한 지연) | 500ms | 0~5,000ms |
    | 실행 간격(반복 사이) | 3초 | 최소 2초 |
    | 실행 시간 제한(1회) | 120초 | 600초 |
    | 단계별 Playwright 대기 제한 | 15초(AI 요약 60초) | — |

  - **실행 결과 기록(SQLite)**: 실행(run) = 실행 ID, 시나리오, 시작·종료 시간, 소요 시간, 성공/실패, 실패 단계, 오류 메시지, 마지막 URL. 단계(step) = 순번, 단계명, 시작·종료, 소요 시간, 성공/실패, 오류 메시지, 페이지 URL, 스크린샷 경로. 실패 시 스크린샷 필수, 성공 단계도 설정에 따라 저장
  - **대시보드(React)**: 대시보드(전체/성공/실패 횟수, 최근 실행) / 시나리오 관리(목록·선택·실행) / 실행 설정 / 실행 이력(날짜·시나리오·성공 여부) / 실행 상세(단계별 결과, 오류 로그, 스크린샷)
  - **환경변수**: `FIXLOG_BASE_URL`, `TEST_ACCOUNT_EMAIL`, `TEST_ACCOUNT_PASSWORD`, `BROWSER_TYPE`, `HEADLESS`, 그리고 추가로 `AUTH_STATE_PATH`(저장된 로그인 상태 파일), `TEST_DOCUMENT_TITLE`(시나리오 대상 테스트 문서 제목), `TEST_SEARCH_KEYWORD`. `.env`는 git에서 제외하고 `.env.example`만 둔다
  - **로그인 방식**: Google은 자동화 브라우저 로그인을 차단하거나 추가 인증(2단계, CAPTCHA)을 요구할 수 있고 이를 우회하지 않는다. 따라서
    1. `python -m app.cli auth` 실행 → headed 브라우저로 `/login` → "Continue with Google" 클릭 → Google 화면에서 `TEST_ACCOUNT_EMAIL`/`TEST_ACCOUNT_PASSWORD`를 입력해 진행 → Google이 추가 확인을 요구하면 **사람이 브라우저에서 직접 완료** → `/workspace` 도착 시 Playwright `storage_state`(localStorage 토큰 포함)를 `AUTH_STATE_PATH`에 저장
    2. 시나리오 실행 시 저장된 상태로 브라우저 컨텍스트를 열어 로그인 상태로 시작. 토큰 만료로 `/login`에 떨어지면 "인증 상태 만료" 실패로 기록하고 1을 다시 하도록 안내
  - **데이터 변경 범위**: AI 요약(문서 자동 저장·버전 기록 생성 포함)과 AI 의미 검색(대화방 생성)은 테스트 계정 안의 변경이므로 허용한다(담당자 결정). 복원·삭제·공유·이동 버튼은 시나리오 단계에 없으므로 누르지 않는다. 버전 기록은 미리보기(읽기 전용)까지만 하고 "현재 버전으로 돌아가기"로 원상태 복귀. AI 요약 후 "AI 추천 태그" 대화상자가 뜨면 적용하지 않고 닫는다. GA4·분석 요청은 차단·변조하지 않는다(route 가로채기 사용 안 함)
  - **대상 문서 선택**: `TEST_DOCUMENT_TITLE`이 있으면 그 제목의 문서, 없으면 문서 목록(`/documents`)의 첫 번째 문서를 대상으로 쓴다. 검색어 `TEST_SEARCH_KEYWORD`가 없으면 대상 문서 제목의 앞부분을 검색어로 쓴다
- 범위 밖:
  - FixLog 원본 프론트·백엔드 수정
  - 문서 생성·삭제·복원·이동·공유, 관리자(`/admin`) 화면
  - CAPTCHA·2단계 인증·봇 탐지 우회, User-Agent 위장, 트래픽 부하 테스트
  - 사용자 인증이 있는 대시보드(로컬 전용으로 실행)
  - 후속 과제: AGENTS.md·architecture.md 템플릿 항목 채우기(이번 작업에서는 수정하지 않음, BAN-004)

## 3. 완료 기준

- 전제: Python 3.12 이상, Node.js 20 이상 설치. 테스트용 Google 계정 1개와 그 계정 워크스페이스에 테스트 문서 1개 이상(본문 있음, 버전 기록 1개 이상). `.env` 작성 완료. 비밀번호는 `.env`에만 둔다

| # | 입력·동작 | 기대 결과 |
|---|----------|----------|
| 1 | `python -m app.cli auth` 실행 후 Google 로그인 완료 | `/workspace` 도착 후 `AUTH_STATE_PATH` 파일 생성, 콘솔에 "인증 상태 저장 완료" |
| 2 | `python -m app.cli run --scenario basic` | 사이트 접속 → 문서 목록 → 문서 상세 단계가 모두 성공, DB에 run 1건·step N건 저장 |
| 3 | `--scenario search` (검색어 = 테스트 문서 제목 일부) | 검색 결과에 테스트 문서 행이 보이고 클릭 시 상세 진입 성공 |
| 4 | `--scenario search` (검색어 = 존재하지 않는 문자열) | "검색 결과 없음"을 검증하는 단계가 성공으로 기록 |
| 5 | `--scenario ai` | AI 패널에 요약 본문이 표시되면 성공. 실패 문구가 보이면 해당 단계 실패 + 스크린샷 저장 |
| 6 | `--scenario version` | 버전 패널이 열리고 v번호 항목 확인, 이전 버전 미리보기 후 현재 버전으로 복귀. 복원 버튼은 누르지 않음 |
| 7 | 인증 상태 파일을 지우고 실행 | 로그인 단계에서 "인증 상태 없음/만료"로 실패 기록, 스크린샷 저장 |
| 8 | 동시 실행 수 5, 실행 횟수 30 요청 | API가 422로 거부(상한 3, 20) |
| 9 | 대시보드에서 시나리오 선택 → 설정 입력 → 실행 | 실행 이력에 진행 중 → 완료 상태가 반영되고 카운트 증가 |
| 10 | 대시보드 실행 상세에서 실패한 실행 열기 | 실패 단계, 오류 메시지, URL, 스크린샷 이미지가 보임 |
| 11 | 저장소 전체에서 테스트 계정 비밀번호 검색 | 소스·로그·DB에 없음 |

## 4. 미결 사항

- 가정: AI 요약은 대상 문서에서 그대로 실행한다. 저장·버전 기록 생성 등 테스트 계정 안의 데이터 변경은 허용(담당자 결정, 2026-11-04)
- 가정: Scenario 2 "검색"은 문서 목록 제목 검색, AI 의미 검색은 별도 시나리오 `ai_search`로 둔다(담당자 결정)
- 가정: 로그인은 사람 보조 1회 로그인 → 인증 상태 저장 → 재사용 방식으로 진행(담당자 결정)
- 가정: 라이브러리 추가 승인. Python 3.15.2 설치 확인. `uvicorn[standard]`는 PyYAML이 Python 3.15 wheel이 없어 설치 실패하므로 `uvicorn`(기본)으로 대체. Python: `playwright`, `fastapi`, `uvicorn`, `python-dotenv`, `pytest`, `httpx` / Frontend: `react`, `react-dom`, `react-router-dom`, `vite`, `@vitejs/plugin-react`(담당자 결정)
- 가정: 최상위에 `backend/`, `frontend/`를 만들고 AGENTS.md·docs/ai 템플릿 항목을 이 프로젝트 기준으로 채운다(담당자 결정)
- 가정: 테스트 계정은 담당자가 `.env`에 직접 넣는다. 테스트 문서는 따로 없으므로 `/documents` 첫 번째 문서를 대상으로 쓴다. 실제 DOM 확인은 담당자가 `auth` 명령을 실행한 뒤 진행(담당자 결정)

## 5. 구현 계획

### 5.1 수정 파일

| 파일 | 구분(신규/수정/삭제/이름 변경) | 변경 내용 |
|------|------------------------------|----------|
| `.gitignore` | 신규 | `.env`, `backend/.auth/`, `backend/data/`, `node_modules/`, `.venv/` 제외 |
| `.env.example` | 신규 | 환경변수 예시(값 없음) |
| `README.md` | 신규 | 설치, 환경변수, 테스트 계정·인증 상태 설정, 실행 방법 |
| `backend/requirements.txt` | 신규 | Python 의존성 |
| `backend/app/config.py` | 신규 | 환경변수 로드, 실행 설정 상한 검증 |
| `backend/app/db.py` | 신규 | SQLite 연결, 테이블 생성(로컬 파일 DB 최초 실행 시) |
| `backend/app/repository.py` | 신규 | run·step·scenario 저장/조회 |
| `backend/app/automation/locators.py` | 신규 | 2장 locator 표를 함수로 모음 |
| `backend/app/automation/browser.py` | 신규 | 브라우저·컨텍스트 생성(인증 상태 로드, 타임아웃) |
| `backend/app/automation/steps.py` | 신규 | 12개 단계 구현과 단계별 검증 |
| `backend/app/automation/scenarios.py` | 신규 | 기본 4개 시나리오 정의, 사용자 정의 시나리오 해석 |
| `backend/app/automation/auth.py` | 신규 | 사람 보조 로그인과 인증 상태 저장 |
| `backend/app/runner.py` | 신규 | 실행 반복·동시 실행(세마포어)·간격·시간 제한, 단계 결과·스크린샷 기록 |
| `backend/app/main.py` | 신규 | FastAPI 앱, API 라우트, 스크린샷 정적 제공 |
| `backend/app/cli.py` | 신규 | `auth`, `run`, `serve` 명령 |
| `backend/tests/test_config.py` | 신규 | 상한·기본값 검증 |
| `backend/tests/test_api.py` | 신규 | API 입력 검증, 이력 조회 |
| `backend/tests/test_steps_fixture.py` | 신규 | FixLog 문구를 흉내 낸 로컬 HTML로 단계·실패 기록·스크린샷 동작 검증(실 사이트 호출 없음) |
| `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html` | 신규 | Vite React 설정(`/api` 프록시) |
| `frontend/src/main.jsx`, `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/src/styles.css` | 신규 | 라우팅, API 호출, 스타일 |
| `frontend/src/pages/Dashboard.jsx`, `Scenarios.jsx`, `RunSettings.jsx`, `History.jsx`, `RunDetail.jsx` | 신규 | 대시보드 5개 화면 |

### 5.2 처리 방식·영향 범위

- 참고 코드: 없음(기존 코드 없음). 사이트 분석은 2장 결과를 따른다
- 처리 순서:
  1. 대시보드(또는 CLI)가 `POST /api/runs`로 시나리오와 설정을 보낸다 → 서버가 상한을 검증하고 batch를 만들어 백그라운드 작업으로 실행
  2. runner가 세마포어(동시 실행 수)로 각 반복을 실행: 브라우저 컨텍스트 생성(인증 상태 로드) → 시나리오의 단계를 순서대로 실행. 각 단계는 locator 상태 기반 대기(`expect(...).to_be_visible()`, `wait_for_url`, 로딩 문구 사라짐) 후 검증하며 고정 sleep은 "단계 사이 대기" 설정에만 쓴다
  3. 단계마다 결과를 DB에 기록. 실패하면 스크린샷·URL·오류를 남기고 이후 단계는 건너뜀 처리, 브라우저 종료 단계는 항상 실행
  4. 대시보드는 `GET /api/runs`, `/api/runs/{id}`, `/api/stats`를 주기적으로 조회해 진행 상태를 갱신
- 영향 범위·리스크:
  - FixLog 배포로 문구가 바뀌면 locator가 깨진다 → `locators.py` 한 곳에 모으고, 실패 시 스크린샷으로 원인 확인
  - 반복 실행이 실제 서비스 트래픽·GA4 데이터에 섞인다 → 동시 3, 반복 20, 간격 2초 이상으로 제한
  - Google 인증 상태가 만료되면 전 실행이 실패한다 → 로그인 단계에서 명확한 메시지로 구분
- 공통 모듈 수정: 없음
- 테이블·컬럼 변경: 운영·공유 DB 변경 없음. 이 프로그램 전용 로컬 SQLite 파일(`backend/data/fixlog_automation.db`)만 프로그램이 직접 만든다
- 배포 시 주의: 로컬 실행 전용. `.env`와 `backend/.auth/`(로그인 토큰 포함)는 커밋·공유하지 않는다

## 6. 결과

### 변경 파일

- `.gitignore` : `.env`, `backend/.auth/`, `backend/data/`, 설치·빌드 결과물 제외
- `.env.example` : 환경변수 예시(값 없음)
- `README.md` : 설치, 환경변수, 테스트 계정 인증, 실행, 시나리오, 상한, 문제 해결
- `backend/requirements.txt` : Python 의존성(버전 고정)
- `backend/pytest.ini` : 테스트 경로 설정 (계획 외)
- `backend/app/__init__.py`, `backend/app/automation/__init__.py` : 패키지 파일 (계획 외)
- `backend/app/config.py` : 환경변수 로드, `RunOptions` 실행 설정과 상한 검증
- `backend/app/constants.py` : 실행·단계 상태 코드 (계획 외)
- `backend/app/schema.sql` : 로컬 SQLite 스키마(SQL-008에 따라 DDL을 파일로 분리) (계획 외)
- `backend/app/db.py` : SQLite 연결, 트랜잭션, 스키마 적용
- `backend/app/repository.py` : 실행·단계·시나리오 쿼리(연결을 받아 실행만)
- `backend/app/service.py` : 실행 기록 업무 로직, 트랜잭션 경계 (계획 외)
- `backend/app/automation/locators.py` : 번들 분석으로 확인한 FixLog 문구·locator
- `backend/app/automation/browser.py` : 브라우저·컨텍스트 생성(인증 상태 로드)
- `backend/app/automation/steps.py` : 12단계 + AI 의미 검색 단계와 단계별 검증
- `backend/app/automation/scenarios.py` : 기본 시나리오 6종, 사용자 정의 시나리오
- `backend/app/automation/auth.py` : 사람 보조 Google 로그인, 인증 상태 저장
- `backend/app/runner.py` : 반복·동시 실행·간격·시간 제한, 단계 기록·스크린샷
- `backend/app/main.py` : FastAPI API, 스크린샷·대시보드 정적 제공
- `backend/app/cli.py` : `auth`, `scenarios`, `run`, `serve` 명령
- `backend/tests/conftest.py`, `backend/tests/fixture_site/index.html` : 테스트용 로컬 서버와 가짜 FixLog 화면 (계획 외)
- `backend/tests/test_config.py`, `backend/tests/test_api.py`, `backend/tests/test_steps_fixture.py` : 자동 테스트 25개
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`, `frontend/index.html` : Vite React 설정
- `frontend/src/main.jsx`, `App.jsx`, `api.js`, `styles.css` : 진입점, 라우팅, API 호출, 스타일
- `frontend/src/hooks.js`, `format.js`, `settings.jsx`, `components.jsx` : 조회 훅, 표시 형식, 실행 설정 Context, 공통 컴포넌트 (계획 외)
- `frontend/src/pages/Dashboard.jsx`, `Scenarios.jsx`, `RunSettings.jsx`, `History.jsx`, `RunDetail.jsx` : 대시보드 화면 5개
- `AGENTS.md`, `docs/ai/workflow.md`, `docs/ai/architecture.md`, `docs/ai/domain.md`, `docs/ai/rules/project.md`, `docs/ai/rules/convention.md`, `docs/ai/rules/backend.md`, `docs/ai/rules/frontend.md`, `docs/ai/rules/sql.md` : 템플릿 `{{ }}`를 이 프로젝트 기준으로 채움. 표준 영역은 원본과 같음을 비교 확인 (계획 외, 담당자 지시)

### 검증

- 빌드: `cd frontend && npm run build` 성공(모듈 50개 변환 완료). 백엔드는 빌드 단계가 없어 import와 `python -m app.cli scenarios`로 확인
- 자동 테스트: `cd backend && .venv\Scripts\python -m pytest` 25개 통과. 가짜 FixLog 화면에 실제 Chromium으로 full, search(결과 없음 포함), ai_search, 대상 문서 지정, 동시 실행 2, 실패 후 건너뜀, 인증 상태 없음을 실행했고, API 상한 422, 시나리오 CRUD, 비밀번호 비노출, 경로 조작을 확인
- 실행 확인:
  - 실제 FixLog 대상 1회 실행: 사이트 접속(제목 FixLog), 로그인 페이지("Continue with Google" 버튼) 성공. 인증 상태가 없을 때 로그인 단계가 안내 메시지와 스크린샷을 남기고 실패하며, 뒤 단계는 건너뛰고 브라우저 종료는 실행됨
  - `python -m app.cli serve` 후 Playwright로 대시보드를 조작: 실행 설정 입력 → 시나리오 선택 → 실행 → 실행 이력 반영 → 실행 상세에서 실패 스크린샷 이미지 로드·오류 로그 확인. 새로고침(`/runs/<id>` 직접 접근) 정상, 브라우저 콘솔 오류 0건, 없는 API 경로 404
  - CLI 종료 코드: 실패한 실행 1, 상한 초과·없는 시나리오 2
  - 로그인 이후 단계(워크스페이스~버전 기록, AI 의미 검색)는 실제 FixLog에서 실행하지 않음. 테스트 계정 인증 상태가 없어서다(PRJ-006)
- 수동 확인 절차:
  1. 저장소 최상위 `.env.example`을 `.env`로 복사하고 `TEST_ACCOUNT_EMAIL`·`TEST_ACCOUNT_PASSWORD`를 채운다
  2. `cd backend && .venv\Scripts\python -m app.cli auth` → 열린 창에서 Google 로그인을 마친다 → 콘솔에 "인증 상태 저장 완료"
  3. `python -m app.cli run --scenario full --headed --screenshots` → 0~12단계가 모두 PASSED인지 본다. 대상 문서 버전 기록이 1개 늘어나는 것이 정상이다(AI 요약의 자동 저장)
  4. `python -m app.cli run --scenario search --keyword 존재하지않는검색어` → "검색 결과 확인" PASSED, "문서 상세 진입" FAILED
  5. `python -m app.cli run --scenario ai_search` → PASSED, FixLog AI 검색 화면에 대화방 1개 생성
  6. `python -m app.cli serve` → http://127.0.0.1:8000 에서 위 실행이 이력·상세에 보이는지 확인한다
  7. 실패가 나면 실행 상세의 스크린샷과 오류를 보고 알려 준다(문구가 바뀌었으면 `locators.py` 수정 대상)

### 완료 기준 결과

| # | 결과(통과/실패/미확인) | 근거 |
|---|----------------------|------|
| 1 | 미확인 | `auth` 명령은 테스트 계정이 필요해 실행하지 않음. 수동 확인 절차 2 |
| 2 | 미확인(실사이트) / 통과(가짜 화면) | 실사이트는 사이트 접속까지 성공 후 인증 상태 없음으로 로그인 실패. 가짜 화면에서는 전 단계 통과(`test_full_scenario_passes_all_steps`, `test_concurrent_runs`) |
| 3 | 미확인(실사이트) / 통과(가짜 화면) | `test_configured_document_title_is_used` |
| 4 | 미확인(실사이트) / 통과(가짜 화면) | `test_search_without_result_records_failure_and_screenshot` |
| 5 | 미확인(실사이트) / 통과(가짜 화면) | full 시나리오의 AI 요약 단계, 추천 태그 대화상자 닫기 포함 |
| 6 | 미확인(실사이트) / 통과(가짜 화면) | full 시나리오의 버전 기록 단계(v2 미리보기 후 복귀, 복원 미실행) |
| 7 | 통과 | 실사이트 실행에서 로그인 단계 실패·스크린샷 저장 확인, `test_login_fails_without_auth_state` |
| 8 | 통과 | `test_run_request_over_limit_is_rejected`(concurrency 5·run_count 30 → 422), CLI 종료 코드 2 |
| 9 | 통과 | 대시보드 조작으로 실행 → 이력 반영 확인, 진행 중일 때 3초 주기 갱신 |
| 10 | 통과 | 실행 상세에서 실패 단계·오류·URL·스크린샷 이미지 표시 확인 |
| 11 | 통과 | `/api/config`가 비밀번호를 내보내지 않음(`test_config_does_not_expose_password`), DB `batches.options_json`에 비밀번호 없음. 실제 비밀번호는 저장소에 없음 |

### 명세와 달라진 점

- AI 패널·버전 기록 패널 locator: 2장 표의 `get_by_role("complementary")` 대신 `aside` 요소 + 패널 제목 텍스트를 쓴다. FixLog 패널은 `<main>` 안의 이름 없는 `<aside>`라 접근성 role이 complementary로 잡히지 않을 수 있어서다
- 문서 행 클릭: 행 가운데 대신 행 안의 제목 텍스트를 누른다. 행 가운데에 더보기 버튼 같은 다른 칸이 올 수 있어서다
- 업무 로직 계층 `backend/app/service.py`를 추가했다. 트랜잭션 경계(BE-002·BE-003)와 호출 방향(ARC-001)을 지키기 위해서다
- `uvicorn[standard]` 대신 `uvicorn`을 쓴다. PyYAML이 Python 3.15용 wheel이 없어 설치에 실패한다
- 랜딩 페이지 "데모 보기" 버튼도 `/documents`로 가는 링크라 로그인이 필요하다. 비로그인 데모는 없다

### 확인 필요

- 테스트 계정으로 `python -m app.cli auth`를 실행한 뒤, 수동 확인 절차 3~6으로 로그인 이후 단계를 실제 FixLog에서 확인해야 한다. 이 결과에 따라 locator를 조정할 수 있다
- BAN-002(운영 서버 접속 금지)와 이 프로그램의 목적(실제 FixLog 서비스 자동 실행)이 겹친다. FixLog 실서비스를 "담당자가 지정한 외부 테스트 대상"으로 볼지 정해 주세요. 지금은 담당자 지시 범위에서 1회 실행(PRJ-005)만 했다
- `docs/ai/git/branch.md`, `docs/ai/git/commit.md`의 브랜치 구성과 AI 커밋 허용 여부는 채우지 않았다. 이 폴더는 아직 git 저장소가 아니다

### 추가 수정 (2026-11-04)

담당자 결정: 규칙 문서는 조직 표준이 아니라 이 저장소 전용이다. 프로젝트에 맞게 고치거나 지운다.

- 변경 파일
  - `AGENTS.md` : BAN-002를 "FixLog에는 브라우저 자동화로만 접속, FixLog API·DB 직접 요청 금지"로, BAN-003을 "ALTER·DROP·TRUNCATE 금지, 스키마는 schema.sql의 CREATE ... IF NOT EXISTS로만"으로 바꿈
  - `docs/ai/workflow.md` : WF-004를 schema.sql 변경 기준으로 바꿈(DBA 검토 삭제)
  - `docs/ai/rules/sql.md` : SQL-008을 schema.sql 기준으로 바꿈, SQL-101 삭제(BAN-003에 합침)
  - `docs/ai/rules/backend.md` : BE-006·BE-007·BE-008과 2장 "로그인 사용자 조회"·"금액·수량 타입"·"파일 업로드" 행 삭제(로그인 사용자·권한·금액·업로드 기능 없음)
  - `docs/ai/rules/common.md` : COM-044 삭제(업로드 기능 없음)
  - `docs/ai/rules/frontend.md` : FE-007 삭제(화면 권한 처리 없음, BE-007 삭제와 함께)
  - `docs/ai/architecture.md` : 8장 "운영" 행을 "FixLog 실서비스(외부), 브라우저 자동화로만 허용"으로 바꿈
  - `AGENTS.md`, `CLAUDE.md`, `docs/ai/**` : `<!-- STANDARD -->` 표시와 "표준 영역" 안내 주석 삭제. "1. 표준 규칙" 제목을 "1. 기본 규칙"으로 바꿈
  - `docs/AI-GUIDE.md` : 표준 배포·비교 절차를 빼고 이 저장소 규칙 문서 관리 가이드로 다시 씀(비어 있는 규칙 번호 목록 포함)
  - `.claude/skills/self-review/SKILL.md` : 삭제한 BE-008 예시를 PRJ-003 예시로 바꿈
  - `docs/specs/_template.md` : 5.2 "테이블·컬럼 변경" 안내의 DBA 검토 문구를 schema.sql 기준으로 바꿈
- 검증: 삭제한 ID(BE-006~008, COM-044, FE-007, SQL-101)와 `STANDARD`·"표준 영역"·"DBA" 문자열을 `grep -rn`으로 검색해 AI-GUIDE의 비어 있는 번호 목록 외에 0건. AGENTS.md 59줄. 코드 변경 없음
- 확인 필요: 위 "확인 필요"의 BAN-002 항목은 이 수정으로 해결됨. 나머지 두 항목(실사이트 로그인 이후 확인, git 설정)은 그대로
