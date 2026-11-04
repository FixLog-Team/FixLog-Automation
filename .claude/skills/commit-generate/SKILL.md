---
name: commit-generate
description: 현재 변경사항을 분석해 docs/ai/git/commit.md 규칙에 맞게 커밋을 나누고 커밋한다. AI 커밋이 금지된 프로젝트에서는 커밋 메시지만 제안한다.
disable-model-invocation: true
allowed-tools: Bash(git *), Read, Glob, Grep
---

# 커밋 생성

규칙은 이 파일에 쓰지 않는다. 형식·type·나누는 기준은 `docs/ai/git/commit.md`, 브랜치 설정은 `docs/ai/git/branch.md`를 읽어 따른다.

## 1. 준비

1. `docs/ai/git/commit.md`와 `docs/ai/git/branch.md`를 읽는다. 1장 설정값을 확인한다.
2. 아래 상태면 커밋하지 않고 안내한 뒤 끝낸다.
   - `git status`에 변경사항이 없다 → "커밋할 변경사항이 없습니다"
   - 머지 충돌 중이다 → "충돌을 먼저 해결하세요"
   - 현재 브랜치(`git branch --show-current`)가 branch.md "직접 push 금지 브랜치"다 → "작업 브랜치에서 실행하세요"
3. 작업ID: 브랜치 이름에서 `SPEC-[0-9]{8}-[a-z0-9-]+`를 찾는다. 없으면 메시지에서 `[작업ID]`를 뺀다.

## 2. 변경 분석

1. `git status`, `git diff`, `git diff --staged`로 변경 파일과 실제 변경 내용을 읽는다. 파일 이름만 보고 판단하지 않는다.
2. commit.md 2장 원칙(GIT-010~013)으로 커밋을 나눈다.
   - 한 파일 안에 성격이 다른 변경이 섞여 있으면 주된 성격 하나로 정한다.
   - 이미지·폰트 같은 바이너리 파일은 `[chore]` 커밋으로 따로 묶는다.
   - `.gitignore` 대상 파일은 넣지 않는다.
   - 커밋이 5개를 넘게 나뉘면 "변경 범위가 커서 리뷰가 어렵습니다"라고 계획에 쓴다.
3. 커밋마다 commit.md 3장 형식으로 메시지를 만든다.

## 3. 커밋

commit.md 1장 "AI 커밋" 값에 따라 다르게 한다.

### "금지"인 경우

커밋하지 않는다. 아래 계획만 출력한다. 사람이 그대로 복사해 실행할 수 있게 명령을 함께 쓴다.

```markdown
## 커밋 제안 (N개)

### 1. [feat] [SPEC-20261104-document-write-scenario] 문서 작성·삭제 시나리오 추가
- backend/app/automation/steps.py
- backend/app/automation/scenarios.py

git add <파일들>
git commit -m "[feat] [SPEC-20261104-document-write-scenario] 문서 작성·삭제 시나리오 추가"
```

### "허용"인 경우

확인을 묻지 않고 바로 커밋한다.

1. 커밋 그룹마다 `git add <해당 파일들>` → `git commit`을 실행한다. 메시지는 여러 줄이면 heredoc으로 넘긴다.
2. 이미 staged된 파일이 다른 그룹에 속하면 `git restore --staged <파일>`로 내린 뒤 다시 나눈다.
3. 커밋이 실패하면 즉시 멈추고 git 오류 메시지를 그대로 보고한다. 다음 커밋으로 넘어가지 않는다.
4. 끝나면 `git log --oneline -N`(N = 만든 커밋 수)을 출력한다.

## 4. 하지 않는 것

- push하지 않는다. push는 `/pr-generate`에서 한다.
- `git commit --amend`, `git reset`, `git rebase`로 기존 커밋을 바꾸지 않는다 (BAN-007).
- `--no-verify`로 hook을 건너뛰지 않는다.
