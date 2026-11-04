# AGENTS.md — FixLog Automation

<!-- 작성 방법은 docs/AI-GUIDE.md를 따른다. 이 파일은 80줄 이내로 유지한다. -->

이 저장소에서 작업하는 모든 AI 도구는 이 파일을 가장 먼저 읽는다.
작업을 시작하기 전에 "4. 문서 지도"에서 해당 작업의 문서를 찾아 읽는다.

## 1. 개요

- 시스템: 외부 서비스 FixLog(https://fix-log-front-theta.vercel.app)에 Playwright 실제 브라우저로 접속해 사용자 여정을 자동 실행하고, 단계별 결과·스크린샷을 기록해 대시보드로 보는 로컬 테스트 도구
- 유형: 풀스택 (FixLog 원본 프론트·백엔드는 이 저장소에 없고 수정하지 않는다)
- 스택: Python 3.15 · FastAPI 0.162 · Playwright 1.64 · SQLite(표준 sqlite3) / React 19.1 · Vite 6.3
- 저장소 구조: backend/=자동화 실행기·API·CLI, frontend/=관리 대시보드, docs/=AI 규칙·작업 명세

## 2. 명령어

| 목적 | 명령 |
|------|------|
| 빌드 | `cd frontend && npm run build` (백엔드는 빌드 단계 없음) |
| 로컬 실행 | `cd backend && .venv\Scripts\python -m app.cli serve` → http://127.0.0.1:8000 |
| 자동 테스트 | `cd backend && .venv\Scripts\python -m pytest` |
| 실제 FixLog 확인 | `cd backend && .venv\Scripts\python -m app.cli run --scenario full --count 1` (PRJ-005, 로그인 상태 필요 PRJ-006) |

작업을 끝내기 전에 `docs/ai/workflow.md` 3장 순서로 검증하고 결과를 보고한다.

## 3. 금지사항

| ID | 금지 | 이유 |
|----|------|------|
| BAN-001 | 비밀번호·API 키·접속 정보를 코드, 로그, 문서에 쓰지 않는다 | 저장소 유출이 곧 시스템 유출이 된다 |
| BAN-002 | FixLog 실서비스에는 이 프로그램의 Playwright 브라우저 자동화로만 접속한다. FixLog API(`https://fixlog.art/fixlog`)·DB에 직접 요청하지 않는다 | 화면 사용자 여정 밖의 조회·변경은 담당자가 승인한 범위가 아니다 |
| BAN-003 | DB에 ALTER·DROP·TRUNCATE를 실행하지 않는다. 스키마는 `backend/app/schema.sql`의 `CREATE ... IF NOT EXISTS`로만 만들고 `init_db`가 적용한다 | 로컬 실행 기록이 지워지거나 기존 DB와 호환이 깨진다 |
| BAN-004 | 요청 범위 밖의 파일·코드를 수정하지 않는다(포맷 정리, 이름 변경 포함) | 리뷰 범위가 커지고 의도하지 않은 변경이 섞인다 |
| BAN-005 | 사람의 승인 없이 라이브러리를 추가·업그레이드·삭제하지 않는다 | 라이선스·보안·호환성 검토가 필요하다 |
| BAN-006 | 실패하는 테스트를 삭제하거나 건너뛰기(skip·ignore 표시, 주석 처리) 처리하지 않는다 | 테스트가 막던 결함이 그대로 배포된다 |
| BAN-007 | push, 강제 push, 브랜치 삭제, 이력 수정(rebase, reset --hard, commit --amend)을 하지 않는다. 예외: 사람이 PR 스킬(`/pr-generate`)을 직접 실행했을 때의 일반 push | 공유 이력은 되돌리기 어렵다 |

| ID | 금지 | 이유 |
|----|------|------|
| BAN-101 | `backend/app/config.py`의 실행 상한(MAX_*, MIN_INTERVAL_SEC)을 높이거나 우회하는 코드를 쓰지 않는다 | 실제 FixLog 서비스 부하와 분석(GA4) 데이터 오염을 막기 위한 담당자 요구다 |
| BAN-102 | FixLog 네트워크 요청을 가로채거나 막거나 바꾸지 않는다(`page.route`, 요청 차단, User-Agent 위장). 예외: `backend/tests`의 가짜 화면 | 정상 분석 요청을 변조하지 않는 것이 담당자 요구다 |
| BAN-103 | Google 로그인의 CAPTCHA·2단계 인증·봇 탐지를 우회하는 코드를 쓰지 않는다 | 계정 보안 기능 우회는 서비스 약관과 보안 정책 위반이다 |
| BAN-104 | `.env`와 `backend/.auth/` 파일 내용을 읽어 출력하거나 커밋하지 않는다 | 테스트 계정 비밀번호와 로그인 토큰이 들어 있다 |

## 4. 문서 지도

| 이런 작업을 할 때 | 이 문서를 읽는다 |
|------------------|-----------------|
| 모든 작업을 시작하기 전 | `docs/ai/workflow.md`, `docs/ai/rules/common.md`, `docs/ai/rules/project.md` |
| 작업 명세를 읽거나 명세 초안을 만들 때 | `docs/specs/_template.md` |
| 코드를 작성·수정할 때 (이름 규칙, 형식) | `docs/ai/rules/convention.md` |
| 처음 보는 모듈·폴더를 다루거나 새 파일의 위치·코드를 둘 레이어를 정할 때 | `docs/ai/architecture.md` |
| 서버 코드(요청 처리·업무 로직·데이터 접근)를 작성·수정할 때 | `docs/ai/rules/backend.md` |
| SQL·쿼리 파일·저장 프로시저를 작성·수정할 때 | `docs/ai/rules/sql.md` |
| 화면 코드(화면 템플릿·컴포넌트·JS·CSS)를 작성·수정할 때 | `docs/ai/rules/frontend.md` |
| 업무 용어·공통코드·업무 규칙·테이블 의미를 확인할 때 | `docs/ai/domain.md` |
| 브랜치를 만들거나 커밋·PR을 만들 때 | `docs/ai/git/branch.md`, `docs/ai/git/commit.md`, `docs/ai/git/pull-request.md` |

이 저장소에 없는 문서의 행은 건너뛴다. 그 문서가 다루는 코드를 새로 만들어야 하면 작업을 멈추고 사람에게 묻는다.
문서 사이의 규칙이 서로 충돌하면 작업을 멈추고 충돌하는 두 규칙의 ID를 사람에게 보고한다.
