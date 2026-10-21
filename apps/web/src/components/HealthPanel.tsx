"use client";

import { useEffect, useState } from "react";
import { getHealth, type Health } from "@/lib/api/client";

type State = { kind: "loading" } | { kind: "success"; health: Health } | { kind: "error"; message: string };

export function HealthPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [request, setRequest] = useState(0);
  useEffect(() => {
    let active = true;
    getHealth().then(health => { if (active) setState({ kind: "success", health }); })
      .catch(error => { if (active) setState({ kind: "error", message: error instanceof Error ? error.message : "状态检查失败" }); });
    return () => { active = false; };
  }, [request]);

  return <section className="surface" aria-labelledby="health-title">
    <div className="section-heading"><div><p className="eyebrow">LOCAL SERVICES</p><h2 id="health-title">本地服务状态</h2></div>
      <button disabled={state.kind === "loading"} onClick={() => { setState({ kind: "loading" }); setRequest(x => x + 1); }}>重新检查</button></div>
    <div role="status" aria-live="polite" aria-atomic="true">
      {state.kind === "loading" && <p className="feedback">正在检查 API 与数据库连接…</p>}
      {state.kind === "error" && <p className="feedback error">{state.message}</p>}
      {state.kind === "success" && <><dl className="service-list">
        <div><dt>Java API</dt><dd>已连接</dd></div><div><dt>MySQL 数据库</dt><dd>已连接</dd></div>
        <div><dt>数据库迁移</dt><dd>版本 {state.health.migrationVersion}</dd></div>
      </dl><p className="muted checked">检查时间：{new Date(state.health.checkedAt).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })}（上海）</p></>}
    </div>
  </section>;
}
