> 当前 Phase 09-R（2026-10-26）已完成固定候选隔离复验，见 [09-R 报告](PHASE_09_R_ACCEPTANCE_REPORT.md) 与 [矩阵](ACCEPTANCE_MATRIX.md)。下文为此前交接审计原文，保留当时结论与证据边界，不能替代本次结果。

# Northstar English Phase 01–09 独立复核交接

审计日期：2026-10-26（Asia/Shanghai）。本目录由只读审计生成，**不构成整体项目验收通过或发布批准**。

## 先读什么

1. [逐阶段汇总](PHASE_01_09_SUMMARY.md)：目标、实现、路径、API/数据库、覆盖、限制和阶段状态。
2. [Phase 09 验收报告](PHASE_09_ACCEPTANCE_REPORT.md)：最终门禁和核心端到端项目。
3. [测试证据](TEST_EVIDENCE.md)：本次实际命令、退出码、历史证据与未执行项目。
4. [架构快照](ARCHITECTURE_SNAPSHOT.md)及[API/数据库快照](API_AND_DATABASE_SNAPSHOT.md)。
5. [已知问题](KNOWN_ISSUES.md)、[四册扩展评估](TEXTBOOK_EXPANSION_ASSESSMENT.md)、[Git 变更](GIT_CHANGE_SUMMARY.md)。
6. [包内逐文件清单](PACKAGE_CONTENTS.md)和 `evidence/` 原始输出（仅作明确说明的路径、凭据、测试对象 ID 脱敏）。

## 结论与证据等级

- Phase 01–08：CONDITIONAL PASS，仅表示当前实现和历史阶段证据支持有限交付；本次未重复全部数据库/浏览器验收。
- Phase 09 和整体交付验收：NOT VERIFIED，存在明确发布阻塞。今天已有历史浏览器成功日志，但已有新增恢复/安全/重复启动成功日志，但与冻结源码的统一全套复验及实体设备测试仍未完成。
- PASS：该明确范围本次实际执行成功；CONDITIONAL PASS：有实现和既有成功证据但有未测条件；FAIL：明确检查失败；NOT VERIFIED：未运行、权限阻塞或证据不足。阶段状态不能替代逐条状态。
- 静态源码、既有报告、既有原始日志、本次运行是四类证据。已有/并行执行日志缺少原始退出码时记为 `null/UNKNOWN`，不由 `passed:true` 伪造退出码 0。

## 本次操作边界

仅新增 `docs/handoff/` 和根目录两个 ZIP；测试生成的缓存/编译输出属于忽略的构建目录。未修改业务源码、配置、已有阶段报告或迁移；未提交 Git。未启动/停止应用、连接数据库执行 SQL、导入/恢复、创建学习记录或录音。单元测试已有临时目录样例/内存 mock 不进入应用数据库，不是新增学习测试数据。

现有应用启动执行 Flyway 和 ContentSeeder，既有学习 E2E 会追加数据，所以不在本次只读范围执行。沙箱 GET 探测失败只说明权限受限，不说明服务停机。数据库前后逐值一致性本次未验证；不得把“本次无写操作”改写为“已核验全库完全不变”。

## 包与复现边界

- `northstar-handoff.zip`：本目录报告、证据、清单和哈希，包含成功及失败记录。
- `northstar-source.zip`：当前工作区源码快照（含未提交 Phase 09 文件）、测试、锁文件、配置模板、迁移、原创示例 JSON、公开技术文档；交接资料在另一包内，无 Git 历史。
- 两包均排除 `.env`、实际凭据、私有配置、数据库导出/备份、个人学习记录/录音、原始服务日志、依赖、缓存和构建产物。原历史阶段报告及私人截图未直接复制；原报告路径用于本地追溯，关键证据另作筛选脱敏副本。
- 原型 HTML/图片、MP3、TTS 生成产物因授权待审及二进制排除规则未入包。**源码包不能单独启动完整课程**：ContentPackage/ContentSeeder 需要原哈希音频，缺失时会拒绝启动，不能生成替代音频冒充复现。
- 此包不证明全新机器安装成功。审查者可先静态审查和运行不依赖音频的单测；完整运行需另行取得经批准的冻结素材、独立本地配置与运行授权。不要直接运行 `db-test`、恢复或写入 E2E 到已有学习库。

`evidence/baseline-files.json`、`evidence/source-integrity.json` 用于核对本次审计源码范围及观察到的并行漂移；`evidence/source-package-files.json`、`evidence/handoff-package-files.json` 提供 ZIP 内容的 SHA-256 清单。根目录 `northstar-packages.sha256` 是压缩包校验和。
