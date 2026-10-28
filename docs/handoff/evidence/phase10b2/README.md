# Phase10B2 证据入口

2026-10-28。整体PASS仅指已测本地隔离工程范围。最终报告：`docs/progress/PHASE_10B_2.md`。

- `INDEPENDENT_10B1_REVIEW.md` / `INDEPENDENT_10B1_SIGNOFF.json`：独立代理技术签收，非人工签字。
- `EXECUTION_SCOPE.md` / `PLAN.md`：用户后续授权、原规划及边界；`PLANNING_REPORT.md`保留原未实施报告。
- `before-development-hashes.json`：开发前真实工作区基线；`stage-files.json`：本阶段最终文件/hash；`delivery-worktree-status.txt`含已有改动和未跟踪文件，不冒称干净工作区或已提交。
- `execution-commands.jsonl`：构建、回归、浏览器和一次性CLI的实际argv/cwd/Git SHA/退出码/日志hash。
- `migration-execution-20261028b/result.json`、各acceptance及commands：升级、最新空库初始化、DDL后故障、新目标恢复；实际SQL/Flyway与身份摘要。私人行值/密码仅在.local，公开日志只放指针/hash。
- `migration-execution/`：保留第一次工具就绪竞态失败批次的原始命令；不作为最终全组PASS。
- `final-data-protection.json`：最终JAR两次普通重启前后38表/媒体一致，旧备份升级/恢复目标再验。
- `nonweb-bootstrap.json`：全新隔离schema无Web一次性初始化成功、重复调用拒绝且全表不变。
- `audio-fixture.json`：自编数学波形的真实MP3编码/PCM解码；不是朗读、教材内容或语音质量证据。
- `failure-events.json`：实际失败、受限环境、修正和重验；退出1或未执行的审批失败未改写为0。
- `delivery-audit.json` / `delivery-audit-commands.json`：4,888份raw日志hash、冻结迁移/内容/依赖、凭据扫描、容器/端口实际状态、个人主站只读health及原JAR不变。
- `DELIVERY_SHA256SUMS.json`：交付文件及本阶段截图的最终SHA-256清单（清单自身不自包含）。早期SHA256SUMS.json保留为规划阶段快照，不混当最终清单。

截图保留 `output/playwright/phase10b2-*.png` 和 `output/playwright/phase10b2-demo/`，未覆盖09-R原图。浏览器pageErrors为空；注入的预期网络/503会出现在console，不称console零错误。实体麦克风/实听/另机/其他浏览器NOT VERIFIED。

个人库仍009.04，主站不运行本阶段新代码；V009.05仅在隔离实例应用。全部6个本轮新建容器已停止、卷保留。不得把此次PASS外推为个人库迁移或10B-3的授权。
