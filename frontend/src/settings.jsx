import { createContext, useContext, useEffect, useState } from "react";

// 실행 설정은 이 브라우저에만 기억한다(편의 기능). 상한 검증은 서버가 한다 (COM-040).
const STORAGE_KEY = "fixlog-automation.run-settings";

export const DEFAULT_RUN_SETTINGS = {
  browser_type: "",
  headless: "",
  run_count: 1,
  concurrency: 1,
  step_delay_ms: 500,
  interval_sec: 3,
  timeout_sec: 180,
  save_success_screenshots: false,
  stop_on_failure: false,
  search_keyword: "",
};

const RunSettingsContext = createContext(null);

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_RUN_SETTINGS, ...JSON.parse(raw) } : DEFAULT_RUN_SETTINGS;
  } catch {
    return DEFAULT_RUN_SETTINGS;
  }
}

export function RunSettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadStored);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // 저장소를 쓸 수 없는 환경(사생활 보호 모드)에서는 이번 세션 동안만 유지한다.
    }
  }, [settings]);
  return <RunSettingsContext.Provider value={{ settings, setSettings }}>{children}</RunSettingsContext.Provider>;
}

export function useRunSettings() {
  return useContext(RunSettingsContext);
}

/** 화면 설정값을 API 요청 형식으로 바꾼다. 빈 값은 서버 기본값(.env)을 쓰도록 보내지 않는다. */
export function toRunRequest(scenarioId, settings) {
  const request = {
    scenario_id: scenarioId,
    run_count: Number(settings.run_count),
    concurrency: Number(settings.concurrency),
    step_delay_ms: Number(settings.step_delay_ms),
    interval_sec: Number(settings.interval_sec),
    timeout_sec: Number(settings.timeout_sec),
    save_success_screenshots: Boolean(settings.save_success_screenshots),
    stop_on_failure: Boolean(settings.stop_on_failure),
  };
  if (settings.browser_type) request.browser_type = settings.browser_type;
  if (settings.headless !== "") request.headless = settings.headless === "true";
  if (settings.search_keyword.trim()) request.search_keyword = settings.search_keyword.trim();
  return request;
}
