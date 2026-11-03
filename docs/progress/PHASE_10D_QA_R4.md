# Phase 10D QA R4 进度

2026-11-02。**FAIL，按新P1停止；同日晚间经用户授权实施修复并通过定向复测，正式关闭待新候选冻结。**

改动文件：新增 qa/phase10d-final-r4/ 的QA运行器、复用原始fixture的种子、浏览器脚本、只读保留和白名单打包工具/证据；新增 docs/qa/phase10d/10D_D02_QA_R4_FINAL.md、10D_FINAL_ACCEPTANCE.md 与本文件。没有修改业务源码、旧测试断言或迁移。

关键决定：保留全部既有工作树；P1原336业务输入不变；独立源代码副本构建；新3380/3381隔离数据库；旧QA草案与现行协议有差异时明确引用现行concept_review_v1。规范化测试遗留污染时保留原库、另建新目标，未删失败现场。

实际命令和结果：`python3 qa/phase10d-final-r4/run.py freeze/create/nodes/regressions/seed`；`python3 qa/phase10d-final-r4/core_checks.py`；`python3 qa/phase10d-final-r4/browser_stack.py`；Playwright MCP加载browser_checks.js；`python3 qa/phase10d-final-r4/preserve.py`；`python3 qa/phase10d-final-r4/package_evidence.py`。精确argv/时间/原退出码在evidence/{commands.jsonl,core/commands.jsonl}；MCP提供断言结果而非进程退出码，不伪造。Node36测试+typecheck/lint/build通过；核心Java11测试与package通过；首轮规范化1项通过；两次失败Java执行完整保留；浏览器真实FAIL。

通过：候选字节/运行构件绑定、新库迁移、Node四项、Java核心回归、API83来源分页与受限白名单。未通过：UI仅前20条，没有分页入口，遗漏63条，唯一可见来源无法回溯。新P1 QA-D02-R4-FINAL-001。

未执行：B08完整并发A-H、B09双重启逐值对账、M03-M08真实恢复/故障矩阵、恢复后续学、浏览器自评/双Tab/断网/丢响应和完整旧Demo/音频回归。新P1发现后未继续执行，不将NOT VERIFIED转换为PASS。

截图：output/playwright/phase10d-final-r4/sources-truncated.png；轨迹同目录sources-truncated-trace.zip。报告与白名单包路径见最终验收。3380/3381和历史失败现场保留；8191/3198子进程已停止；未连接个人3308、未重启3100/8085、未提交/合并/推送/部署。

下一阶段依赖：CORE最小修复、冻结新候选，独立QA受影响复测并补齐剩余发布门槛。停止，不进入10E。

修复补记（同日晚）：用户授权"解决新缺陷"后修改 `apps/web/src/components/review/ConceptReviewCard.tsx`（nextCursor逐页加载、attemptId:occurrenceId去重合并、"已显示 X/Y 条可见"、加载更多与错误重试），未改API/JAR/迁移。`qa/phase10d-final-r4/fix_stack.py` 增加 `API_PORT=8191` 重建步骤：复测首次失败是旧`.next`构建把8085代理固化进routes-manifest。复测命令：`python3 qa/phase10d-final-r4/fix_stack.py`（含fix-web-build）与 `node qa/phase10d-final-r4/run_fix_browser.cjs`；83/83来源（82受限+1可见）浏览器PASS，截图 sources-fixed.png；`fix-node-test/typecheck/lint`与`fix-web-build`均exit0。证据：evidence/fix-runtime.json、fix-browser-result.json、fix-*.log、commands.jsonl；独立证据包 northstar-phase10d-fix-verification-evidence.zip。仍未执行B08/B09/M03–M08；8191/3198子进程已停止，未连接个人3308、未重启3100/8085、未提交/合并/推送/部署。

交付校验：白名单420个文件已实际独立解压并运行verify.py通过（exit0）；git diff --check通过（exit0）。证据包最终SHA-256以同名.zip.sha256为准，避免包内报告自引用哈希。
