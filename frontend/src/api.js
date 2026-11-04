// FastAPI 백엔드 호출 모음. 비밀 정보는 이 코드에 두지 않는다 (FE-008).

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(formatError(body) ?? `요청 실패 (HTTP ${response.status})`);
  }
  return body;
}

function formatError(body) {
  if (!body?.detail) return null;
  if (typeof body.detail === "string") return body.detail;
  return body.detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join(", ");
}

export const api = {
  getConfig: () => request("/api/config"),
  getStats: () => request("/api/stats"),
  getSteps: () => request("/api/steps"),
  getScenarios: () => request("/api/scenarios"),
  createScenario: (scenario) => request("/api/scenarios", { method: "POST", body: JSON.stringify(scenario) }),
  deleteScenario: (id) => request(`/api/scenarios/${encodeURIComponent(id)}`, { method: "DELETE" }),
  startRun: (options) => request("/api/runs", { method: "POST", body: JSON.stringify(options) }),
  getRuns: ({ limit = 20, offset = 0, status = "", scenarioId = "" } = {}) => {
    const params = new URLSearchParams({ limit, offset });
    if (status) params.set("status", status);
    if (scenarioId) params.set("scenario_id", scenarioId);
    return request(`/api/runs?${params}`);
  },
  getRun: (id) => request(`/api/runs/${encodeURIComponent(id)}`),
};

export function screenshotUrl(path) {
  return `/screenshots/${path.split("/").map(encodeURIComponent).join("/")}`;
}
