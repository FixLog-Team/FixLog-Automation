import { Link } from "react-router-dom";
import { RUN_STATUS_LABEL, formatDateTime, formatDuration } from "./format.js";

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status?.toLowerCase()}`}>{RUN_STATUS_LABEL[status] ?? status}</span>;
}

export function LoadingState() {
  return <p className="muted">불러오는 중…</p>;
}

export function ErrorState({ message }) {
  return <p className="error-box" role="alert">{message}</p>;
}

export function EmptyState({ children }) {
  return <p className="muted empty">{children}</p>;
}

export function RunTable({ runs }) {
  if (runs.length === 0) return <EmptyState>실행 이력이 없습니다.</EmptyState>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>실행 시각</th>
            <th>시나리오</th>
            <th>회차</th>
            <th>결과</th>
            <th>실패 단계</th>
            <th>소요 시간</th>
            <th>브라우저</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>
                <Link to={`/runs/${run.id}`}>{formatDateTime(run.started_at ?? run.created_at)}</Link>
              </td>
              <td>{run.scenario_name}</td>
              <td>#{run.iteration}</td>
              <td><StatusBadge status={run.status} /></td>
              <td className="error-text">{run.failed_step ?? ""}</td>
              <td>{formatDuration(run.duration_ms)}</td>
              <td className="muted">{run.browser_type}{run.headless ? "" : " (headed)"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
