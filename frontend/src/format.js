export const RUN_STATUS_LABEL = {
  QUEUED: "대기",
  RUNNING: "실행 중",
  PASSED: "성공",
  FAILED: "실패",
  SKIPPED: "건너뜀",
};

export const IN_PROGRESS_STATUSES = ["QUEUED", "RUNNING"];

export function formatDateTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

export function formatDuration(ms) {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
