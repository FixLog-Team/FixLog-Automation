# 프론트엔드 규칙

<!-- 이 문서의 역할: 대시보드(frontend/, React SPA) 화면 코드 규칙이다. -->

## 1. 기본 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| FE-001 | 서버·사용자 데이터를 화면에 출력할 때 2장 "출력 이스케이프 방법"으로 HTML 이스케이프한다. 2장 "금지 출력 방식"을 쓰지 않는다 | 이스케이프하지 않으면 XSS 공격이 가능하다 |
| FE-002 | 화면 입력 검증을 추가하면 같은 검증이 서버에 있는지 확인한다. 서버가 같은 저장소면 서버 검증을 함께 구현하고(COM-040), 다른 저장소면 완료 보고의 "확인 필요"에 쓴다 | 화면 검증은 사용 편의용이고 우회할 수 있다 |
| FE-003 | 3장 "공통 컴포넌트"에 있는 기능은 공통 컴포넌트를 쓴다. 같은 기능을 새로 만들지 않는다 | 화면마다 동작이 달라지고 수정 지점이 늘어난다 |
| FE-005 | 저장·삭제 버튼은 요청이 끝날 때까지 다시 누를 수 없게 한다 | 중복 클릭으로 같은 데이터가 두 번 저장된다 |
| FE-006 | 삭제처럼 되돌릴 수 없는 동작은 실행 전에 확인 메시지를 띄운다 | 실수로 누른 버튼이 데이터 손실이 된다 |
| FE-008 | 브라우저로 전달되는 코드·환경 변수(빌드 시 번들에 들어가는 값)에 비밀 정보를 넣지 않는다. 비밀 정보가 필요한 호출은 서버를 거친다 (BAN-001) | 번들 파일은 누구나 내려받아 읽을 수 있다 |

## 2. 이 프로젝트의 화면 기술

<!-- 화면 기술의 버전은 architecture.md 1장에 쓴다. 공통 함수·컴포넌트는 3장에 쓴다. -->
| 항목 | 값 | 위치(파일) |
|------|----|-----------|
| 화면 기술 | React + JavaScript(JSX) | `frontend/src` |
| 렌더링 방식 | SPA | `frontend/src/main.jsx` |
| API 서버 위치 | 같은 저장소(`backend/`) | `backend/app/main.py` |
| 출력 이스케이프 방법 | React JSX 기본 출력 `{값}` | |
| 금지 출력 방식 | `dangerouslySetInnerHTML`, `innerHTML` 대입 | |
| 라이브러리와 버전 | react 19.1.0, react-dom 19.1.0, react-router-dom 7.6.0 | `frontend/package.json` |
| UI 컴포넌트 | 없음(직접 만든 CSS) | `frontend/src/styles.css` |
| 상태 관리 | React Context(실행 설정만) | `frontend/src/settings.jsx` |
| 공통 스타일 | styles.css | `frontend/src/styles.css` |
| 화면 파일 위치와 이름 규칙 | 화면 하나에 `pages/PascalCase.jsx` 하나, 경로는 `App.jsx` `Routes`에 등록 | `frontend/src/pages`, `frontend/src/App.jsx` |

- 본보기 화면(목록형): `frontend/src/pages/History.jsx`
- 본보기 화면(입력형): `frontend/src/pages/RunSettings.jsx`

## 3. 공통 컴포넌트

| 기능 | 컴포넌트·함수 | 위치 | 사용 예시 파일 |
|------|-------------|------|--------------|
| 서버 호출 | `api.*`, `screenshotUrl` | `frontend/src/api.js` | `frontend/src/pages/Scenarios.jsx` |
| 서버 조회·주기 갱신 | `useServerData` | `frontend/src/hooks.js` | `frontend/src/pages/History.jsx` |
| 실행 설정 상태 | `useRunSettings`, `toRunRequest` | `frontend/src/settings.jsx` | `frontend/src/pages/Scenarios.jsx` |
| 상태 배지·로딩·오류·빈 목록 | `StatusBadge`, `LoadingState`, `ErrorState`, `EmptyState` | `frontend/src/components.jsx` | `frontend/src/pages/RunDetail.jsx` |
| 실행 목록 표 | `RunTable` | `frontend/src/components.jsx` | `frontend/src/pages/Dashboard.jsx` |
| 날짜·소요 시간·상태 이름 | `formatDateTime`, `formatDuration`, `RUN_STATUS_LABEL` | `frontend/src/format.js` | `frontend/src/components.jsx` |

## 4. 프로젝트 추가 규칙

| ID | 규칙 | 이유 |
|----|------|------|
| FE-101 | 서버 조회는 `useServerData`로 하고 데이터·로딩·오류 상태를 함께 화면에 반영한다 | 화면마다 로딩·오류 처리가 달라지지 않게 한다 |
| FE-102 | 로딩·오류·빈 목록 표시는 `LoadingState`·`ErrorState`·`EmptyState`를 쓴다 | FE-003 |
| FE-103 | 실행 설정 상한은 `/api/config`의 `limits` 값으로 화면에 표시하고, 화면에 숫자를 따로 쓰지 않는다 | 상한은 서버(`config.py`) 한 곳에서 정한다 (BE-102) |
