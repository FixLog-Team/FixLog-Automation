---
name: pr-generate
description: 현재 브랜치의 커밋을 분석해 docs/ai/git/pull-request.md 형식으로 PR 제목·본문을 만들고, push한 뒤 PR을 생성한다.
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *), Read, Glob, Grep
---

# PR 생성

규칙은 이 파일에 쓰지 않는다. PR 형식은 `docs/ai/git/pull-request.md`, 기준 브랜치는 `docs/ai/git/branch.md`, type은 `docs/ai/git/commit.md`를 읽어 따른다.
이 스킬은 사람이 직접 실행했을 때만 push한다 (BAN-007 예외).

## 1. 준비

1. 위 세 문서를 읽고 1장 설정값을 확인한다. 기준 브랜치 = branch.md "PR 기준 브랜치".
2. 아래 상태면 멈추고 안내한다.
   - 현재 브랜치가 branch.md "직접 push 금지 브랜치"다 → "작업 브랜치에서 실행하세요"
   - `git log {기준 브랜치}..HEAD`에 커밋이 없다 → "PR로 올릴 커밋이 없습니다"
   - `git status`에 커밋하지 않은 변경이 있다 → "커밋하지 않은 변경이 있습니다. /commit-generate를 먼저 실행할까요?"라고 묻는다

## 2. 내용 분석

1. `git log {기준 브랜치}..HEAD`와 `git diff {기준 브랜치}...HEAD`로 커밋과 실제 변경 내용을 읽는다.
2. 브랜치 이름에서 `SPEC-[0-9]{8}-[a-z0-9-]+`를 찾는다. 있으면 `docs/specs/{SPEC ID}.md`를 읽는다.
   - 명세가 있으면 본문은 pull-request.md 3장의 괄호 안 명세 장에서 옮겨 쓴다.
   - 명세 5.1 수정 파일과 실제 변경 파일이 다르면 본문 "참고"에 다른 파일을 적는다.
   - 명세가 없으면 커밋과 diff만으로 쓴다.
3. 제목은 pull-request.md 2장, 본문은 3장 형식으로 만든다. 작업 유형은 하나만 체크한다.

## 3. push와 PR 생성

1. `git push`로 현재 브랜치를 올린다. 원격 추적 브랜치가 없으면 `git push -u origin {현재 브랜치}`를 쓴다.
   - 강제 push(`--force`, `--force-with-lease`)는 하지 않는다. push가 거절되면 멈추고 원인을 보고한다.
2. pull-request.md 1장 "PR 생성 명령"에 기준 브랜치, 제목, 본문을 넘겨 PR을 만들고 PR 주소를 출력한다.
3. PR 생성이 실패하면 오류 메시지를 그대로 보고하고, 만든 제목·본문을 출력한다.

## 4. 하지 않는 것

- 기준 브랜치나 직접 push 금지 브랜치로 push하지 않는다.
- 브랜치를 삭제하거나 rebase하지 않는다 (BAN-007).
- PR을 머지하지 않는다. 머지는 사람이 리뷰 후 한다.
