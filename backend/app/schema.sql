-- 이 프로그램 전용 로컬 SQLite 파일(backend/data/fixlog_automation.db)의 스키마.
-- 공유·운영 DB가 아니며, 앱이 시작할 때 없는 테이블만 만든다.

CREATE TABLE IF NOT EXISTS batches (
    id              TEXT PRIMARY KEY,
    scenario_id     TEXT NOT NULL,
    options_json    TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    finished_at     TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    batch_id        TEXT NOT NULL REFERENCES batches(id),
    iteration       INTEGER NOT NULL,
    scenario_id     TEXT NOT NULL,
    scenario_name   TEXT NOT NULL,
    browser_type    TEXT NOT NULL,
    headless        INTEGER NOT NULL,
    status          TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    duration_ms     INTEGER,
    failed_step     TEXT,
    error_message   TEXT,
    last_url        TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_runs_batch_id ON runs(batch_id);

CREATE TABLE IF NOT EXISTS run_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(id),
    seq             INTEGER NOT NULL,
    step_id         TEXT NOT NULL,
    step_name       TEXT NOT NULL,
    status          TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    duration_ms     INTEGER,
    page_url        TEXT,
    detail          TEXT,
    error_message   TEXT,
    screenshot_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_steps_run_id ON run_steps(run_id);

CREATE TABLE IF NOT EXISTS custom_scenarios (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    steps_json      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
