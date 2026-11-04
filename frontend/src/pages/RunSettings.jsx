import { api } from "../api.js";
import { ErrorState, LoadingState } from "../components.jsx";
import { useServerData } from "../hooks.js";
import { DEFAULT_RUN_SETTINGS, useRunSettings } from "../settings.jsx";

export default function RunSettings() {
  const config = useServerData(api.getConfig);
  const { settings, setSettings } = useRunSettings();
  const update = (key) => (event) => {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setSettings({ ...settings, [key]: value });
  };

  if (config.isLoading) return <LoadingState />;
  if (config.error) return <ErrorState message={config.error} />;
  const limits = config.data.limits;

  return (
    <>
      <header className="page-header">
        <h1>실행 설정</h1>
        <button className="secondary" onClick={() => setSettings(DEFAULT_RUN_SETTINGS)}>기본값으로</button>
      </header>

      <section className="card">
        <h2>실행</h2>
        <div className="form-grid">
          <NumberField label="실행 횟수" value={settings.run_count} onChange={update("run_count")}
            min={1} max={limits.max_run_count} hint={`최대 ${limits.max_run_count}회`} />
          <NumberField label="동시 실행 수" value={settings.concurrency} onChange={update("concurrency")}
            min={1} max={limits.max_concurrency} hint={`최대 ${limits.max_concurrency}개`} />
          <NumberField label="단계 사이 대기(ms)" value={settings.step_delay_ms} onChange={update("step_delay_ms")}
            min={0} max={limits.max_step_delay_ms} step={100} hint="사람과 비슷한 속도로 진행하기 위한 대기" />
          <NumberField label="실행 간격(초)" value={settings.interval_sec} onChange={update("interval_sec")}
            min={limits.min_interval_sec} max={limits.max_interval_sec} step={0.5}
            hint={`반복 실행 시작 사이 간격, 최소 ${limits.min_interval_sec}초`} />
          <NumberField label="1회 실행 시간 제한(초)" value={settings.timeout_sec} onChange={update("timeout_sec")}
            min={limits.min_timeout_sec} max={limits.max_timeout_sec} hint={`최대 ${limits.max_timeout_sec}초`} />
          <label>
            검색어
            <input value={settings.search_keyword} onChange={update("search_keyword")} maxLength={100}
              placeholder={config.data.test_search_keyword || "비우면 대상 문서 제목 앞부분"} />
            <small>검색 시나리오의 제목 검색어, AI 의미 검색 시나리오의 질문</small>
          </label>
        </div>
      </section>

      <section className="card">
        <h2>브라우저</h2>
        <div className="form-grid">
          <label>
            브라우저 종류
            <select value={settings.browser_type} onChange={update("browser_type")}>
              <option value="">.env 기본값 ({config.data.browser_type})</option>
              <option value="chromium">chromium</option>
              <option value="firefox">firefox</option>
              <option value="webkit">webkit</option>
            </select>
            <small>firefox·webkit은 <code>playwright install firefox webkit</code> 필요</small>
          </label>
          <label>
            실행 모드
            <select value={settings.headless} onChange={update("headless")}>
              <option value="">.env 기본값 ({config.data.headless ? "headless" : "headed"})</option>
              <option value="true">Headless (화면 없음)</option>
              <option value="false">Headed (브라우저 창 표시)</option>
            </select>
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={settings.save_success_screenshots}
              onChange={update("save_success_screenshots")} />
            성공한 단계도 스크린샷 저장 (실패 단계는 항상 저장)
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={settings.stop_on_failure}
              onChange={update("stop_on_failure")} />
            첫 실패에서 멈춤 (해제하면 실패를 기록하고 다음 단계 계속, 앞 단계가 필요한 단계만 건너뜀)
          </label>
        </div>
      </section>

      <section className="card">
        <h2>환경(.env, 읽기 전용)</h2>
        <dl className="kv">
          <dt>대상 URL</dt><dd>{config.data.base_url}</dd>
          <dt>테스트 계정</dt><dd>{config.data.account_email || "미설정"} {config.data.has_password ? "(비밀번호 설정됨)" : ""}</dd>
          <dt>인증 상태</dt><dd>{config.data.has_auth_state ? "저장됨" : "없음 — python -m app.cli auth 실행 필요"}</dd>
          <dt>대상 문서</dt><dd>{config.data.test_document_title || "미설정 (문서 목록 첫 문서)"}</dd>
        </dl>
      </section>
    </>
  );
}

function NumberField({ label, hint, ...props }) {
  return (
    <label>
      {label}
      <input type="number" {...props} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
