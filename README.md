# FixLog Automation

[FixLog](https://fix-log-front-theta.vercel.app)에 실제 브라우저(Playwright)로 접속해 사용자 여정을 자동 실행하고,
단계별 성공/실패·스크린샷·소요 시간을 기록해 React 대시보드에서 보는 로컬 프로그램입니다.
FixLog 원본 프로젝트는 수정하지 않습니다.

```
backend/   Python · FastAPI · Playwright · SQLite (자동화 실행기, API, CLI)
frontend/  React · Vite (관리 대시보드)
docs/specs/  작업 명세(요구사항, FixLog 화면 분석, 변경 기록)
docs/ai/     AI 개발 규칙(AGENTS.md에서 시작)
```

## 1. 준비물

| 항목 | 버전 | 확인 |
|------|------|------|
| Python | 3.12 이상 (3.15.2에서 확인) | `python --version` |
| Node.js | 20 이상 (24에서 확인) | `node --version` |
| 테스트용 Google 계정 | FixLog에 로그인할 수 있는 계정 | |

> Windows에서 Python을 방금 설치했다면 새 터미널을 열어야 `python` 명령이 잡힙니다.

## 2. 설치

```bash
# 백엔드
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # firefox, webkit도 쓰려면: python -m playwright install firefox webkit

# 대시보드
cd ../frontend
npm install
npm run build                   # 빌드 결과(frontend/dist)를 백엔드 서버가 함께 제공한다
```

> **이후 모든 `python` 명령은 `backend` 폴더에서, 가상환경을 켠 상태로 실행합니다.**
> 켠 상태면 프롬프트 앞에 `(.venv)`가 붙습니다. 켜지 않으려면 `python` 대신 `.venv\Scripts\python`을 쓰세요.
> 라이브러리는 `backend/.venv` 안에만 설치되므로, PC에 설치된 Python으로 실행하면 `No module named ...` 오류가 납니다.

## 3. 환경변수 설정

저장소 최상위에서 `.env.example`을 `.env`로 복사하고 값을 채웁니다. `.env`는 git에 올라가지 않습니다.

| 변수 | 필수 | 설명 |
|------|------|------|
| `FIXLOG_BASE_URL` | | 대상 주소. 기본값 `https://fix-log-front-theta.vercel.app` |
| `TEST_ACCOUNT_EMAIL` | | 테스트 Google 계정 이메일(로그인 칸 자동 입력용) |
| `TEST_ACCOUNT_PASSWORD` | | 테스트 Google 계정 비밀번호(로그인 칸 자동 입력용, 로그·DB에 남지 않음) |
| `BROWSER_TYPE` | | `chromium`(기본) / `firefox` / `webkit` |
| `HEADLESS` | | `true`(기본, 화면 없음) / `false`(창 표시) |
| `AUTH_STATE_PATH` | | 로그인 상태 파일. 기본 `backend/.auth/state.json` |
| `DATA_DIR` | | 실행 결과 DB·스크린샷 폴더. 기본 `backend/data` |
| `TEST_DOCUMENT_TITLE` | | 대상 문서 제목. 비우면 문서 목록의 첫 번째 문서. 문서 작성 단계가 있는 실행은 작성한 문서를 쓴다 |
| `TEST_SEARCH_KEYWORD` | | 검색어/AI 질문. 비우면 대상 문서 제목 앞 10자. 문서 작성 단계가 있는 실행은 작성한 문서 제목을 쓴다 |

## 4. 테스트 계정 설정 (최초 1회)

FixLog는 Google OAuth만 지원하고, 로그인 토큰을 브라우저 localStorage에 저장합니다.
Google은 자동화 브라우저에 2단계 인증이나 추가 확인을 요구할 수 있고, 이 프로그램은 그런 절차를 **우회하지 않습니다**.
그래서 사람이 한 번 로그인해 저장한 상태를 이후 실행에서 재사용합니다.
`auth`는 처음 한 번, 그리고 로그인 상태가 만료됐을 때만 실행합니다. 실행할 때마다 새로 로그인하는 명령이라 매번 로그인 창이 뜹니다.

```bash
cd backend
.venv\Scripts\activate
python -m app.cli auth
```

1. 브라우저 창이 열리고 FixLog 로그인 페이지에서 "Continue with Google"이 자동으로 눌립니다.
2. `.env`에 계정이 있으면 이메일과 비밀번호를 자동으로 입력합니다. 비워 두면 열린 창에서 직접 입력하면 됩니다.
3. Google이 2단계 인증, 계정 선택, "안전하지 않은 브라우저" 같은 확인을 띄우면 **열린 창에서 직접 완료**하세요. 기본 대기 시간은 300초이며 `--wait 600`으로 늘릴 수 있습니다.
4. FixLog 워크스페이스가 열리면 로그인 상태가 `backend/.auth/state.json`에 저장되고 창이 닫힙니다.

- 로그인 상태가 만료되면 시나리오의 "로그인" 단계가 "로그인 상태가 만료되었습니다"로 실패합니다. 그때 `auth`를 다시 실행하세요.
- `backend/.auth/state.json`에는 로그인 토큰이 들어 있습니다. 공유하거나 커밋하지 마세요.
- Google이 자동화 브라우저 로그인 자체를 막으면 `.env`에 `BROWSER_TYPE=firefox`로 바꾸고 `python -m playwright install firefox` 후 다시 시도해 보세요.

## 5. 실행

### 대시보드 (권장)

```bash
cd backend
.venv\Scripts\activate
python -m app.cli serve          # http://127.0.0.1:8000
```

브라우저에서 http://127.0.0.1:8000 을 엽니다.

| 화면 | 내용 |
|------|------|
| 대시보드 | 전체/성공/실패 횟수, 성공률, 최근 실행, 시나리오별 결과, 로그인 상태 안내 |
| 시나리오 | 시나리오 목록·선택·실행 버튼, 단계를 골라 사용자 정의 시나리오 만들기 |
| 실행 설정 | 실행 횟수, 동시 실행 수, 단계 사이 대기, 실행 간격, 시간 제한, 브라우저 종류·모드, 검색어 |
| 실행 이력 | 실행 날짜, 시나리오, 성공 여부, 실패 단계(결과·시나리오 필터) |
| 실행 상세 | 실패 화면 스크린샷, 오류 로그, 단계별 결과·URL·소요 시간 |

대시보드를 고치면서 보려면 백엔드 서버를 띄운 상태에서 `cd frontend && npm run dev`(http://localhost:5173)를 실행하세요.

### 명령줄

```bash
python -m app.cli scenarios                              # 시나리오 목록
python -m app.cli run --scenario basic                   # 1회 실행 후 단계별 결과 출력
python -m app.cli run --scenario search --keyword 결제
python -m app.cli run --scenario full --headed --screenshots
python -m app.cli run --scenario full --stop-on-failure  # 첫 실패에서 멈춤
python -m app.cli run --scenario basic --count 5 --concurrency 2 --interval 5 --delay-ms 800 --timeout 180
```

모든 실행이 성공하면 종료 코드 0, 하나라도 실패하면 1을 돌려줍니다.

## 6. 시나리오와 단계

| 시나리오 ID | 이름 | 단계 |
|------------|------|------|
| `basic` | 기본 탐색 | 사이트 접속 → 로그인 → 워크스페이스 진입 → 문서 목록 조회 → 문서 상세 진입 → 브라우저 종료 |
| `search` | 검색 | 로그인 → 워크스페이스 → 문서 목록 → 검색어 입력 → 검색 결과 확인 → 결과 문서 진입 → 종료 |
| `ai` | AI 기능 | 로그인 → 문서 목록 → 문서 상세 → AI 요약 실행·결과 확인 → 종료 |
| `version` | 버전 관리 | 로그인 → 문서 목록 → 문서 상세 → 버전 기록 조회·이전 버전 미리보기 → 종료 |
| `ai_search` | AI 의미 검색 | 로그인 → 워크스페이스 → 홈에서 AI 검색 질문·답변 확인 → 종료 |
| `write` | 문서 작성·삭제 | 로그인 → 워크스페이스 → 새 문서 만들기 → 제목·본문 작성 → 저장 → 새로고침 후 저장 내용 확인 → 문서 삭제 → 휴지통 확인 → 종료 |
| `full` | 전체 사용자 여정 | 1~4단계(접속·로그인 페이지·로그인·워크스페이스) → 문서 작성·저장·확인 → 작성한 문서로 5~10단계(목록·검색·상세·AI 요약·버전 기록) → 작성한 문서 AI 의미 검색 → 문서 삭제·휴지통 확인 → 11~12단계(다른 페이지 이동·종료) |

데이터 변경 주의(담당자 승인 완료):
- **문서 작성·삭제**(`write`, `full`): 실행할 때마다 FixLog 최상위에 `자동화 테스트 문서 날짜 시간 xxxx` 문서를 만들고, 끝에 그 문서만 삭제합니다. 삭제한 문서는 휴지통에 남습니다(영구 삭제·복원은 하지 않음). 쌓이면 FixLog 휴지통에서 직접 비우세요. 문서 작성 단계가 있는 실행은 이 문서로 검색·AI 요약·버전 기록을 합니다.
- **AI 요약**: FixLog의 "요약" 버튼은 요약 전에 문서를 저장합니다. 그래서 실행할 때마다 대상 문서의 버전 기록이 늘 수 있습니다. 요약 후 뜨는 "AI 추천 태그" 대화상자는 태그를 추가하지 않고 닫습니다.
- **AI 의미 검색**: FixLog 서버에 대화방이 하나 생성됩니다(자동 삭제하지 않음).
- **버전 기록**: 미리보기만 하고 "현재 버전으로 돌아가기"로 복귀합니다. 복원·삭제·공유·이동 버튼은 누르지 않습니다.
- GA4 등 분석 요청은 차단하거나 변조하지 않습니다. 자동 실행도 FixLog 분석 데이터에 집계됩니다.

## 7. 실행 상한

실제 서비스에 붙는 자동화이므로 서버가 아래 범위를 벗어난 요청을 422로 거부합니다. 실행 요청(batch)은 한 번에 하나만 받습니다.

| 항목 | 기본값 | 허용 범위 |
|------|-------|----------|
| 실행 횟수 | 1 | 1~20 |
| 동시 실행 수 | 1 | 1~3 |
| 단계 사이 대기 | 500ms | 0~5000ms |
| 실행 간격(반복 시작 사이) | 3초 | 2~600초 |
| 1회 실행 시간 제한 | 180초 | 10~600초 |

## 8. 실행 결과 기록

- DB: `backend/data/fixlog_automation.db`(SQLite). 테이블 `runs`(실행 ID, 시작·종료 시간, 시나리오, 성공/실패, 실패 단계, 오류, 마지막 URL, 소요 시간), `run_steps`(단계별 결과·URL·스크린샷 경로·소요 시간)
- 스크린샷: `backend/data/screenshots/<실행 ID>/<순번>_<단계>.png`. 실패한 단계는 항상 저장하고, 성공한 단계는 "성공 단계도 스크린샷 저장"을 켰을 때만 저장합니다.
- 단계가 실패해도 기본적으로 실패를 기록하고 다음 단계를 계속합니다. 앞 단계 결과가 필요한 단계(예: 문서 작성이 실패하면 저장·삭제)만 "'문서 작성' 실패로 실행하지 않음"으로 건너뜁니다. 브라우저 실행 실패와 실행 시간 제한 초과 때는 나머지를 모두 건너뜁니다. 첫 실패에서 멈추려면 실행 설정 "첫 실패에서 멈춤" 또는 CLI `--stop-on-failure`를 쓰세요. 실패 단계 칸에는 처음 실패한 단계가 남습니다.

## 9. 테스트

```bash
cd backend
.venv\Scripts\activate
python -m pytest
```

`tests/fixture_site/`의 가짜 FixLog 화면(실제 화면 문구·구조를 흉내 냄)에 실제 Chromium으로 시나리오를 돌립니다.
실제 FixLog 서버에는 요청하지 않습니다.

## 10. 문제 해결

| 증상 | 조치 |
|------|------|
| `No module named 'app'` | `backend` 폴더로 이동해서 실행 |
| `No module named 'pydantic'`(또는 playwright 등) | 가상환경을 켜지 않았음. `.venv\Scripts\activate` 후 실행 |
| AI 요약 "AI 요약에 실패했습니다"·AI 검색 "답변 생성에 실패했습니다" | FixLog AI 쪽 오류. 기존 문서 대상 `ai` 시나리오도 실패하면 FixLog AI 장애이므로 나중에 다시 실행 |
| 로그인 단계 "저장된 로그인 상태가 없습니다" | 4장 `python -m app.cli auth` 실행 |
| 로그인 단계 "로그인 상태가 만료되었습니다" | `auth` 다시 실행 |
| 문서 목록 조회 "최상위에 문서가 없습니다" | 폴더 안에만 문서가 있으면 `.env`의 `TEST_DOCUMENT_TITLE`에 문서 제목 지정 |
| AI 요약 "문서 본문이 비어 있어" | 본문이 있는 문서를 `TEST_DOCUMENT_TITLE`로 지정 |
| 단계가 `Timeout ... exceeded`로 실패 | 실행 상세의 스크린샷 확인. FixLog 화면 문구가 바뀌었으면 `backend/app/automation/locators.py`만 고치면 됩니다 |
| `pip install`에서 PyYAML 빌드 실패 | `uvicorn[standard]` 대신 `requirements.txt`의 `uvicorn`을 쓰세요(Python 3.15용 PyYAML wheel 없음) |

## 11. 알려진 문제

- 터미널에서 `run`이 도는 중에 `serve`를 시작하면, 서버가 시작 정리 과정에서 그 실행을 "서버가 재시작되어 실행이 중단되었습니다"로 실패 처리합니다. 실행이 끝나면 실제 결과로 다시 기록되지만, 그 전까지 대시보드에 실패로 보입니다. 서버는 실행이 없을 때 시작하세요.
- 기본 대시보드 설정값을 바꿔도 브라우저에 저장된 예전 실행 설정(시간 제한 등)이 남아 있으면 그 값을 씁니다. 실행 설정 화면에서 값을 확인하세요.
- FixLog 동작: 문서 목록에서 검색한 뒤 그 문서를 삭제하고 같은 검색어로 다시 검색하면, 새로고침 전까지 삭제한 문서가 보입니다. 자동화의 삭제 확인 단계는 새로고침 후 확인합니다.
