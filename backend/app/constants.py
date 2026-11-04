"""실행·단계 상태 코드. 문자열을 코드에 직접 쓰지 않고 이 상수를 쓴다 (COM-007)."""


class RunStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class StepStatus:
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


IN_PROGRESS_RUN_STATUSES = (RunStatus.QUEUED, RunStatus.RUNNING)
