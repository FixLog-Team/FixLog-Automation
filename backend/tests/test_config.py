import pytest
from pydantic import ValidationError

from app.config import MAX_CONCURRENCY, MAX_RUN_COUNT, RunOptions, load_settings


@pytest.mark.parametrize("field, value", [
    ("concurrency", MAX_CONCURRENCY + 2),
    ("concurrency", 0),
    ("run_count", MAX_RUN_COUNT + 10),
    ("interval_sec", 1),
    ("timeout_sec", 601),
    ("step_delay_ms", 5001),
    ("browser_type", "edge"),
])
def test_run_options_rejects_values_over_limit(field, value):
    with pytest.raises(ValidationError):
        RunOptions(scenario_id="basic", **{field: value})


def test_run_options_defaults():
    options = RunOptions(scenario_id="basic")
    assert (options.run_count, options.concurrency, options.interval_sec) == (1, 1, 3.0)


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("FIXLOG_BASE_URL", "https://example.test/")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("BROWSER_TYPE", "Firefox")
    settings = load_settings()
    assert settings.base_url == "https://example.test"
    assert settings.headless is False
    assert settings.browser_type == "firefox"


def test_load_settings_rejects_unknown_browser(monkeypatch):
    monkeypatch.setenv("BROWSER_TYPE", "ie")
    with pytest.raises(ValueError):
        load_settings()
