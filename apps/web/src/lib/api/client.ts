export type Health = {
  status: "UP";
  database: "UP";
  project: string;
  migrationVersion: string;
  checkedAt: string;
};

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function getHealth(timeoutMs = 5000): Promise<Health> {
  let response: Response;
  try {
    response = await fetch("/api/v1/health", {
      cache: "no-store", signal: AbortSignal.timeout(timeoutMs),
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new ApiError("暂时无法连接本地服务，请确认服务已启动后重试。", 0, "NETWORK_ERROR");
  }
  if (!response.ok) {
    throw new ApiError("本地服务或数据库暂不可用，请检查启动日志后重试。", response.status, "SERVICE_UNAVAILABLE");
  }
  let data: unknown;
  try { data = await response.json(); } catch {
    throw new ApiError("服务返回了无法识别的状态。", response.status, "INVALID_RESPONSE");
  }
  if (!data || typeof data !== "object" || !("status" in data) || data.status !== "UP"
    || !("database" in data) || data.database !== "UP"
    || !("project" in data) || data.project !== "northstar-english-local-v1"
    || !("migrationVersion" in data) || typeof data.migrationVersion !== "string"
    || !("checkedAt" in data) || typeof data.checkedAt !== "string" || !Number.isFinite(Date.parse(data.checkedAt))) {
    throw new ApiError("服务返回了无法识别的状态。", response.status, "INVALID_RESPONSE");
  }
  return data as Health;
}
