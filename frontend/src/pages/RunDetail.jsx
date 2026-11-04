import { Link, useParams } from "react-router-dom";
import { api, screenshotUrl } from "../api.js";
import { ErrorState, LoadingState, StatusBadge } from "../components.jsx";
import { IN_PROGRESS_STATUSES, formatDateTime, formatDuration } from "../format.js";
import { useServerData } from "../hooks.js";

export default function RunDetail() {
  const { runId } = useParams();
  const run = useServerData(() => api.getRun(runId), [runId], {
    pollWhile: (d) => d && IN_PROGRESS_STATUSES.includes(d.status),
  });

  if (run.isLoading && !run.data) return <LoadingState />;
  if (run.error) return <ErrorState message={run.error} />;
  const r = run.data;
  const failedSteps = r.steps.filter((s) => s.status === "FAILED");

  return (
    <>
      <header className="page-header">
        <h1>실행 상세</h1>
        <Link to="/runs">← 실행 이력</Link>
      </header>

      <section className="card">
        <dl className="kv">
          <dt>실행 ID</dt><dd><code>{r.id}</code></dd>
          <dt>시나리오</dt><dd>{r.scenario_name} <code>{r.scenario_id}</code> · #{r.iteration}회차</dd>
          <dt>결과</dt><dd><StatusBadge status={r.status} /></dd>
          <dt>시작</dt><dd>{formatDateTime(r.started_at)}</dd>
          <dt>종료</dt><dd>{formatDateTime(r.finished_at)}</dd>
          <dt>소요 시간</dt><dd>{formatDuration(r.duration_ms)}</dd>
          <dt>브라우저</dt><dd>{r.browser_type} ({r.headless ? "headless" : "headed"})</dd>
          {r.failed_step && <><dt>실패 단계</dt><dd className="error-text">{r.failed_step}</dd></>}
          {r.last_url && <><dt>마지막 URL</dt><dd className="break">{r.last_url}</dd></>}
        </dl>
      </section>

      {failedSteps.length > 0 && (
        <section className="card card-error">
          <h2>실패 화면과 오류 로그</h2>
          {failedSteps.map((s) => (
            <div key={s.id} className="failure">
              <h3>{s.seq}. {s.step_name}</h3>
              {s.page_url && <p className="muted break">URL: {s.page_url}</p>}
              <pre className="log">{s.error_message}</pre>
              {s.screenshot_path && <Screenshot path={s.screenshot_path} alt={`${s.step_name} 실패 화면`} />}
            </div>
          ))}
        </section>
      )}

      <section className="card">
        <h2>단계별 결과</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>단계</th><th>결과</th><th>소요</th><th>내용</th><th>URL</th><th>화면</th></tr>
            </thead>
            <tbody>
              {r.steps.map((s) => (
                <tr key={s.id} className={s.status === "FAILED" ? "row-failed" : ""}>
                  <td>{s.seq}</td>
                  <td>{s.step_name}</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td>{formatDuration(s.duration_ms)}</td>
                  <td className="detail">{s.error_message ? s.error_message.split("\n")[0] : s.detail}</td>
                  <td className="muted break">{s.page_url ? new URL(s.page_url).pathname : ""}</td>
                  <td>{s.screenshot_path && <a href={screenshotUrl(s.screenshot_path)} target="_blank" rel="noreferrer">보기</a>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {IN_PROGRESS_STATUSES.includes(r.status) && <p className="muted">실행 중… 3초마다 갱신합니다.</p>}
      </section>
    </>
  );
}

function Screenshot({ path, alt }) {
  const url = screenshotUrl(path);
  return (
    <a href={url} target="_blank" rel="noreferrer">
      <img className="screenshot" src={url} alt={alt} loading="lazy" />
    </a>
  );
}
