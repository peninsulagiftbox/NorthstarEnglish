# Phase 10E 课程导入流水线交付记录

日期：2026-11-05（Asia/Shanghai）；本地测试部署补记：2026-11-11。状态：实现与隔离验证完成；已部署到独立本地测试实例。样例来源仍是 `pending_review`，正式发布前必须人工审校；未进入 10F。

## 改动内容

1. **core-v1 读取与验证**：新增 `CoreContent`。它加载原 `package.json` 与外部 `manifest.json`，执行 Draft 2020-12 Schema、重复键拒绝、路径/大小/软链接边界、规范化 SHA-256、transcript-v1、来源审校与许可、音频解码与哈希、知识/题目跨引用和练习语义校验。结果返回可审查 issues，不使用异常掩盖正负例。
2. **导入生命周期**：新增 `ContentImport` 与 `ContentImportCli`。流程为离线 `validate`、零写入 `dry-run`、显式 `apply`、崩溃后 `resume`、事后 `verify` 和显式 `publish`。apply 按顺序执行媒体先落地、数据库事务、审计状态标记和恢复指针；publish 复用 `ContentPublication` 并在发布前重新加载完整导入包核验哈希与可验证性。系统状态沿 `validated/staged/materialized/applied/published/partial_failed` 推进。
3. **数据库迁移**：V013.01–V013.04 新增 `import_batch`、`import_entry` 和单一 `content-import` 互斥行。数据库状态只记录导入审计和恢复锚点；原课程、句子、资产、知识和练习投影在现有表中保留。`ContentSeeder` 的空库检查排除 seeded mutex；`ExportController` 将三张导入审计表纳入冻结校验。
4. **发布契约与导入审计**：`lesson.json` 的 `importPackageId` 是导入来源指针。发布前会按 packageId 重新读取完整导入包，要求包未被替换、哈希一致且仍能通过 core-v1 验证。已发布的 `lesson_version.payload_json` 保留完整原包。
5. **原创样例与源工具**：新增原创 A/B 两课，分别 12/24 句；A 有共享课段音轨，B 有独立句音频。macOS 合成语音仅用于本地隔离验证，不表示公开再分发。新增受限输入/媒体检测、PDF 本地抽取、正负例、浏览器检查、隔离环境、升级矩阵、备份/恢复和 `data-transfer.py` 内容媒体支持。
6. **UI 与端到端**：导入页支持上传冻结包、展示 dry-run 计划、显式批准与结果反馈；`ContentSeeder` 只在空库播种 Demo，导入课不覆盖既有数据。Playwright 覆盖导入页、真实媒体播放、恢复、练习与答案隐私。

## 样例与审校边界

- A/B 样例路径为 `.local/phase10e/samples/{a,b}`，包身份分别为 `sample-a-v1-package`、`sample-b-v1-package`；内容哈希分别为 `130b861f5644096936ea5a681317be906201fea3269c9ec3f8a681fd0f0e4b47`、`7c98b105c45ca4cf9dc61b03e936156393168cc005bf4693f80c11a32b7c3cf4`。
- 样例文本与音频来源均为 `sourceType=original`、`rightsScope=local_test_only`、`reviewStatus=pending_review`；`reviewer` 为空。`reviewedAt` 只表示校对记录时间，不是人工审校结论。
- 两课未显式发布。导入测试可先 `apply` 为隔离草稿/validated 状态，再由有真实授权的人确认来源后调用显式 publish。人工听查未完成，因此正式发布验收仍被阻塞。

## 隔离目标与安全边界

- CLI 目标必须满足：`MYSQL_PORT` 已配置且不为 3308；`DB_NAME` 只能是 `northstar_english`、`northstar_phase01_test`，或显式 `NORTHSTAR_ALLOW_RESTORE_DB=true` 时的 `northstar_restore_YYYYMMDDHHMMSS`；`NORTHSTAR_IMPORT_DB_UUID` 必须等于目标 `@@server_uuid`，且禁止交接摘要中的个人 UUID；`NORTHSTAR_IMPORT_MEDIA_ROOT` 和 `DB_IMPORT_PASSWORD` 必须提供。
- CLI 不隐式运行迁移，不接受目标外的 schema，失败时保留现场并提示 `status/verify/resume`。
- 所有 Java/浏览器/工具验证均在隔离目标执行；个人 3308、8085、3100 未写入、未停止、未读取学习记录。

## 验证结果

以下结果均来自当前 Phase 10E 工作区；`phase10e.py sync` 先复制源码到 `.local/phase10e/source`，再在副本运行命令。日志与结构化结果保留在 `docs/handoff/evidence/phase10e/`。

| 检查 | 命令/结果 | 证据 |
| --- | --- | --- |
| Java 全量回归 | `apps/api/mvnw -f apps/api/pom.xml test`：51/51 PASS，0 失败，0 错误 | `java-regression-final-*.log` |
| 隔离导入生命周期 | `ContentImportIntegrationTest` PASS：同包幂等 `no_op`、计划过期拒绝、media drift 拒绝、A/B 投影与练习数量正确、答案/存储键不外泄 | `validation-isolated-*.log` |
| 导入恢复 | `ContentImportRecoveryIntegrationTest` PASS：媒体/数据库故障后恢复、stale plan、无练习空态、版本 CAS、异包冲突 | `import-recovery-expanded-*.log` |
| 备份恢复再导入 | `ContentImportRestoreIntegrationTest` PASS：恢复库读回 A/B，接受第三门独立课程 | `restored-new-import-*.log` |
| 升级与故障矩阵 | 老库、DDL fault、history fault、恢复目标全部保留旧行/媒体并迁移至 `013.04`；异常目标不自动修复 | `upgrade-result.json`、`upgrade-*.log` |
| 数据传输工具 | 24 项 Python 检查 PASS，含 COMPLETE、导入表、内容媒体备份/恢复与生成列 | `python-final-*.log`、`transfer-*.json` |
| Web 静态与构建 | `typecheck`、`lint`、`test`、`build` 全部 exit 0 | `web-*.log` |
| 导入页真实浏览器 | A/B 真实媒体、恢复、5/12 题练习、答案隐私、空练习、历史版本通过 | `imports-browser-result.json`、`imports-browser-*.log` |
| 旧 Demo 回归 | 首页/目录/播放/作答/复习/草稿/暂停/无 AI 检查通过 | `demo-browser-result.json` |
| 最新确定性冒烟 | `CoreContentTest` 5 项：0 失败，2 项环境用例跳过；重复至第 80 次 PASS | `tests-final-check-80-*.log` |

## 未解决问题与风险

1. **未通过正式人工验收**：没有真人审校文本/许可证，也没有真人听查音频；样例不能发布为可再分发内容。机器 PASS 不改变这个结论。
2. **macOS 系统语音**：只用于本地隔离验证，遵守系统许可，不得对外分发或转换为通用授权证明。
3. **测试夹具与真实来源隔离**：损坏包、越界路径、错误哈希和 synthetic-contract-fixture 均仅用于测试，不冒充正式课或人工验收。
4. **证据清单完整性**：`SHA256SUMS` 覆盖证据目录除自身与 `execution-commands.jsonl` 外的内容；`evidence-manifest.json` 是冻结源/输出清单。证据目录曾因自引用清单膨胀，交付前已固定；评审前不再重复生成。
5. **四册教材未导入**：本阶段只实现流水线和两门原创样例；不解析、不导入四册教材，也不建立批量抓取流程。

## 交付物

- 本报告：`docs/progress/PHASE_10E.md`
- 使用指南：`docs/phase10/10E_IMPORT_USER_GUIDE.md`
- 设计增量：`docs/phase10/06_CONTENT_IMPORT_PIPELINE.md`
- 实施计划：`docs/phase10/10E_IMPLEMENTATION_PLAN.md`
- 证据与清单：`docs/handoff/evidence/phase10e/`
- 消毒证据包：`output/review/northstar-phase10e-sanitized-evidence.zip`

下一阶段仍不应开始。需先完成人工审校、真人听查、发布演练授权与评审，再决定是否进入 10F。

## 本地隔离测试部署补记（2026-11-11）

- 在新建的 Phase 10E 专用 MySQL 容器和空白 `northstar_phase01_test` schema 上完成迁移、运行账号授权与 Demo 播种；未连接、停止或修改个人本地实例，也未触碰正式服务。
- API：`http://127.0.0.1:18185`；Web：`http://127.0.0.1:13185`。健康检查返回 `UP`，Flyway 版本 `013.04`；Web 经同源代理健康检查也返回 `UP`。
- 部署 JAR SHA-256：`f8f6ec7c556ccbb1d8797dcb237ee4f27ebe8c158208bb12987b169ab1ddba3b`；Next.js BUILD_ID：`_MnGFW6CWx0KTGtz83Qat`。
- 本次候选副本验证：前端 typecheck、43 项测试、lint、build，后端 `CoreContentTest`，Python 内容工具测试均退出 0；Maven package 退出 0。
- 全量隔离数据库回归仍以 [本地完整测试记录](PHASE_LOCAL_FULL_TEST.md) 为准：55 项中 52 通过、1 失败、1 错误、1 跳过；未修改断言掩盖失败。
- 两门导入样例仍为 `pending_review`，没有执行课程发布。本地测试部署不代表人工审校、正式素材授权或 10F 获批。
