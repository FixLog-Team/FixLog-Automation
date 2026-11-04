import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ErrorState, LoadingState, RunTable } from "../components.jsx";
import { formatDateTime, formatDuration } from "../format.js";
import { useServerData } from "../hooks.js";

const RECENT_RUN_COUNT = 10;

export default function Dashboard() {
  const stats = useServerData(api.getStats, [], { pollWhile: (d) => d?.in_progress > 0 });
  const runs = useServerData(() => api.getRuns({ limit: RECENT_RUN_COUNT }), [], {
    pollWhile: () => stats.data?.in_progress > 0,
  });
  const config = useServerData(api.getConfig);

  return (
    <>
      <header className="page-header">
        <h1>대시보드</h1>
        <Link className="button" to="/scenarios">시나리오 실행</Link>
      </header>

      {config.data && <AuthNotice config={config.data} />}

      {stats.error && <ErrorState message={stats.error} />}
      {stats.isLoading && !stats.data && <LoadingState />}
      {stats.data && <StatTiles stats={stats.data} />}

      <section className="card">
        <h2>최근 실행 결과</h2>
        {runs.error && <ErrorState message={runs.error} />}
        {runs.data && <RunTable runs={runs.data.items} />}
        <Link to="/runs">전체 이력 보기 →</Link>
      </section>

      {stats.data?.by_scenario.length > 0 && (
        <section className="card">
          <h2>시나리오별 결과</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>시나리오</th><th>실행</th><th>성공</th><th>실패</th><th>성공률</th></tr>
              </thead>
              <tbody>
                {stats.data.by_scenario.map((row) => (
                  <tr key={row.scenario_id}>
                    <td>{row.scenario_name}</td>
                    <td>{row.total}</td>
                    <td className="ok-text">{row.passed}</td>
                    <td className="error-text">{row.failed}</td>
                    <td>{row.total ? `${Math.round((row.passed / row.total) * 100)}%` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

function StatTiles({ stats }) {
  const finished = stats.passed + stats.failed;
  const rate = finished ? `${Math.round((stats.passed / finished) * 100)}%` : "-";
  return (
    <div className="tiles">
      <Tile label="전체 실행" value={stats.total} />
      <Tile label="성공" value={stats.passed} tone="ok" />
      <Tile label="실패" value={stats.failed} tone="error" />
      <Tile label="성공률" value={rate} />
      <Tile label="진행 중" value={stats.in_progress} />
      <Tile label="평균 소요" value={formatDuration(stats.avg_duration_ms)} />
    </div>
  );
}

function Tile({ label, value, tone }) {
  return (
    <div className={`tile ${tone ? `tile-${tone}` : ""}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
    </div>
  );
}

function AuthNotice({ config }) {
  if (config.has_auth_state) {
    return (
      <p className="notice">
        테스트 계정 인증 상태 저장됨 ({formatDateTime(config.auth_state_updated_at)}) · 대상 {config.base_url}
      </p>
    );
  }
  return (
    <p className="notice notice-warn">
      저장된 로그인 상태가 없습니다. 터미널에서 <code>python -m app.cli auth</code>를 실행해 테스트 계정으로 한 번
      로그인하세요. 그 전에는 로그인 이후 단계가 실패합니다.
    </p>
  );
}
