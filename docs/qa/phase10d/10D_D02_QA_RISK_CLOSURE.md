# D02 风险补证与 CORE 最小复现

日期：2026-11-02。结论：**FAIL，停止签收**。业务源码与冻结 JAR 未改。

此前将“不存在的 DELETE 端点返回 404”视为撤回权限通过不成立，本轮已撤销该判断。此前“双写者足以排除所有更高并发问题”也不成立；本轮已实际补测有限并发。

## 执行状态

| 原风险 | 行动与实际结果 | 状态 |
| --- | --- | --- |
| 撤回受限来源 | 在全新 3364 合成副本将 cr-a 设为 withdrawn；真实浏览器刷新来源列表显示服务错误。默认 limit=20 与 limit=1 均 500，limit=100 返回 200。发现 P1 QA-D02-R4-BUG-001。 | FAIL，交 CORE |
| 并发规模 | 16 同时 HTTP 写者 × 10 轮；每轮 8 个错误 Attempt + 8 个同 rowVersion 自评。160 请求，90 次成功命令重放；每轮自评仅1赢家，另外7个409；80来源全部保留，10结果，90回执，80新Attempt；卡唯一、无重复来源、无孤儿结果、due与结果一致、quiz_run未变。 | PASS（仅此有界规模，非无限并发保证） |
| M05/M06 复用容器 | 新命名空间 northstar-d02-risk-20261102，新容器/新卷/新UUID，3363–3371。upgrade/empty双路径各双启动一致；7项故障实验全部新建环境执行，已提交DDL/history/旧值对账通过，失败目标保留。 | PASS，9份验收JSON |
| 浏览器栈脚本 | 原 /private/tmp/qa-r3 已丢失；重建持久脚本 qa_runtime.py/browser_stack.py/browser_checks.js/run_checked.py，记录真实子进程退出码、身份、构建输入与产物哈希。专有子进程已停止，失败库保留。 | 已补归档；浏览器业务验收被P1阻断 |
| 用户签收 | 生成本报告、缺陷最小复现、更新最终验收结论与新证据包。 | 暂停签收；待CORE修复后重新独立QA |

## QA-D02-R4-BUG-001（P1）

影响：存在撤回来源且一页达到 limit、最后一条为 restricted 时，来源接口稳定500；正常浏览器使用默认20条即触发，受限占位与后续来源页无法读取。未在此路径观察到正文泄露；接口可用性和分页已失败。

候选：27文件清单 087f849df28d66d1c80d48e5328322c3c385c152ea3ea65313e87b5f4703b787；JAR cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb。

目标：全新 empty 角色容器 northstar-d02-risk-20261102-empty，127.0.0.1:3364，northstar_phase01_test。UUID、卷、容器ID见 logs/fixture-clone.json。账号 local；API 8186，Web3197。3350只读复制合成夹具，3348/3349原现场未操作，3308未连接。

前提：真实错误Attempt形成概念卡 f87999e5-8838-4981-b2a2-c616c5d3eb96 与来源；lesson cr-a 在本轮合成副本已设 withdrawn。测试后83来源：82个cr-a（restricted）、1个cr-b（visible）。

最小请求（保留现场上无需写库）：

```http
GET /api/v1/concept-reviews/f87999e5-8838-4981-b2a2-c616c5d3eb96/sources?limit=1
X-Northstar-Request: local-workspace
Origin: http://127.0.0.1:3197
```

实际：500 INTERNAL_ERROR，retryable=false；日志 NullPointerException at ConceptReviewController.sources(ConceptReviewController.java:130)。对照 limit=100：200，82受限行仅含白名单字段。此对照仅用于定位，不是规避方案。

原因：sources() 对原 row 调用 keySet().retainAll，移除了 cursorKey（第122行），但第130行 rows.getLast().get("cursorKey").toString() 仍引用同一个被修改的 Map。达到整页且页尾为restricted时必现。建议CORE保存原分页键后再裁剪对外字段，并加 limit=1/20、页尾restricted、下一页可继续读取的真实MySQL/HTTP回归。QA本轮未修改实现。

复现脚本：scripts/reproduce_sources.py。浏览器复现：运行 browser_stack.py，打开 /review → 全部概念卡 → 学习来源，显示“本地服务发生错误”。原始HTTP响应、traceId、内部堆栈及浏览器DOM均存 logs。

## 证据与停止边界

目录 qa/phase10d/evidence/d02-risk-closure；新包 output/review/northstar-phase10d2-risk-closure-evidence.zip。原R3报告与包保留为历史证据，新报告撤销其无条件PASS。

保留第一次clone连接未就绪、栈端口TIME_WAIT误判、浏览器分页/等待失败等真实记录；未以管道退出码代替子命令退出码。迁移命令每条原退出码、私有原日志哈希及脱敏DDL/Flyway日志另存。

依用户原停止要求，P1发现后停止后续验收签收，保存现场并交CORE。本轮未修业务、未提交/合并/推送/部署、未进入10E。
