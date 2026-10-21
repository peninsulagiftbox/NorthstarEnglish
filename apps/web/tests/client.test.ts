import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, getHealth } from "../src/lib/api/client.ts";

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
test("accepts actual health response", async () => {
  const health = { status: "UP", database: "UP", project: "northstar-english-local-v1", migrationVersion: "001", checkedAt: new Date().toISOString() };
  globalThis.fetch = async () => Response.json(health);
  assert.deepEqual(await getHealth(), health);
});
test("database outage remains an error and hides server details", async () => {
  globalThis.fetch = async () => Response.json({ detail: "secret database password" }, { status: 503 });
  await assert.rejects(getHealth(), (e: unknown) => e instanceof ApiError && e.status === 503 && !e.message.includes("secret"));
});
test("rejects malformed or different-project UP responses", async () => {
  globalThis.fetch = async () => Response.json({ status: "UP", database: "UP", project: "other" });
  await assert.rejects(getHealth(), (e: unknown) => e instanceof ApiError && e.code === "INVALID_RESPONSE");
});
test("timeout produces a recoverable connection error", async () => {
  globalThis.fetch = async (_url, init) => new Promise((_resolve, reject) => {
    init?.signal?.addEventListener("abort", () => reject(new DOMException("timeout", "TimeoutError")), { once: true });
    setTimeout(() => reject(new Error("test timeout guard")), 50);
  });
  await assert.rejects(getHealth(5), (e: unknown) => e instanceof ApiError && e.code === "NETWORK_ERROR");
});
