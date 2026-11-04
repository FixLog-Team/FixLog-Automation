import { useState } from "react";
import { api } from "../api.js";
import { ErrorState, LoadingState, RunTable } from "../components.jsx";
import { IN_PROGRESS_STATUSES, RUN_STATUS_LABEL } from "../format.js";
import { useServerData } from "../hooks.js";

const PAGE_SIZE = 20;
const STATUS_FILTERS = ["", "PASSED", "FAILED", "RUNNING", "QUEUED"];

export default function History() {
  const [page, setPage] = useState(0);
  const [status, setStatus] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const scenarios = useServerData(api.getScenarios);
  const runs = useServerData(
    () => api.getRuns({ limit: PAGE_SIZE, offset: page * PAGE_SIZE, status, scenarioId }),
    [page, status, scenarioId],
    { pollWhile: (d) => d?.items.some((r) => IN_PROGRESS_STATUSES.includes(r.status)) },
  );
  const totalPages = runs.data ? Math.max(1, Math.ceil(runs.data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <header className="page-header">
        <h1>실행 이력</h1>
        <button className="secondary" onClick={runs.reload}>새로고침</button>
      </header>
      <section className="card">
        <div className="filters">
          <label>
            결과
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(0); }}>
              {STATUS_FILTERS.map((s) => <option key={s} value={s}>{s ? RUN_STATUS_LABEL[s] : "전체"}</option>)}
            </select>
          </label>
          <label>
            시나리오
            <select value={scenarioId} onChange={(e) => { setScenarioId(e.target.value); setPage(0); }}>
              <option value="">전체</option>
              {scenarios.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          {runs.data && <span className="muted">총 {runs.data.total}건</span>}
        </div>
        {runs.error && <ErrorState message={runs.error} />}
        {runs.isLoading && !runs.data && <LoadingState />}
        {runs.data && <RunTable runs={runs.data.items} />}
        <div className="pager">
          <button className="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>이전</button>
          <span>{page + 1} / {totalPages}</span>
          <button className="secondary" disabled={page + 1 >= totalPages} onClick={() => setPage(page + 1)}>다음</button>
        </div>
      </section>
    </>
  );
}
