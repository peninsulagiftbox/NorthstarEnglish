# Phase 10D-D01-R 独立修复复验报告

日期：2026-11-01（Asia/Shanghai）。结论：**D01 复验 PASS（附 1 项候选提交前置条件，见 §8）**。所有结果绑定同一冻结候选：Git HEAD `ff0dbe1f8b89a1817c2f5a0e7ba0755d5f971188` + 主工作区未提交 10D 候选（89 个文件，逐文件 SHA-256 见 `qa/phase10d/evidence/candidate-sha256.txt`，清单哈希 `a3cd11c79e984fa66ad360d2c00d4d364f7c8b1f7f0265516eba9c328b130726`）。

复验环境：既有 QA worktree `test/10d-qa`（只读基线）+ 3340 隔离 MySQL 容器 `northstar-phase10c2-20261031d-empty`（server_uuid `7ca8f0fc-d50a-11f1-b8e2-92808e97a3e8`，命名空间 `-20261031d`，API 8176 / Web 3196 回环）。个人库 3308 与个人服务 3100/8085 全程未连接、未触碰。目标身份、Flyway 历史与触发器清单见 `qa/phase10d/evidence/final-target-identity.json`（56 表、46 条迁移全部 success=1、012.01–012.07 已应用）。

## 1. 冻结与迁移历史

1. 候选源码从主工作区同步进 QA worktree 与隔离构建副本，冻结清单覆盖全部未提交/新增文件（含 `knowledge/` 包、V012_01–V012_07、测试与脚本）。关键迁移 SHA-256：V012_01 `bd27beaf…c67593c`、V012_02 `cb1e7b0e…d3edf3f`、V012_07 `528dbdbd…e36df85`（完整值见冻结清单）。原始字节摘录见 `qa/phase10d/evidence/migration-bytes.txt`。
2. 已应用迁移的数据库身份：3340 容器内 `northstar_english`（CORE 自建升级库）、`northstar_phase01_test`（测试库）、`northstar_restore_20261101024700`（QA 探针库）均绑定同一候选迁移字节。迁移仅存在于上述隔离容器与 QA worktree，未进入 `origin/main` 或共享分支，未应用于任何个人/不可丢弃环境。
3. 未执行 repair、未修改任何 flyway_schema_history、未清理任何失败库；失败现场（见 §6）原样保留。

## 2. 七项缺陷复验（均实测）

| 缺陷 | 复验方式与证据 | 结果 |
| --- | --- | --- |
| QA-BUG-001 lesson 级重复 occurrence | 探针库 `northstar_restore_20261101024700` 直插两条同 version+revision lesson-scope 记录，第二条 `1062 Duplicate entry 'qa7-v1-qa7-rev-L' for uq_occurrence_location`（`qa7-immutable-probe2` 日志）；N-07 同证 | PASS |
| QA-BUG-002 Unicode 空白规范化 | `KnowledgeConceptsTest` 4/4 + `KnowledgeNormalizationIntegrationTest` 1/1 通过（`knowledge-normalization-1793468868902371000.log`） | PASS |
| QA-BUG-003 attempt 快照不可变 | 探针库 UPDATE/DELETE 均 `45000 Attempt knowledge snapshots are immutable`（`qa7-immutable-probe5`）；runtime 账号 UPDATE/DELETE `1142` 拒绝（N-13） | PASS |
| QA-BUG-004 修订不可变 + 哈希覆盖 | 探针库修订 UPDATE/DELETE 均 `45000 Knowledge concept revisions are append-only`（`qa7-immutable-probe`/N-14）；`relations_sha256` 含修订内容的代码在冻结候选 `KnowledgeRegistrationCli.relationsHash` 内核对 | PASS |
| QA-BUG-005 撤回课聚合泄露 | `KnowledgeSourcesIntegrationTest` browse 段：撤回后 `lessonCount` 降至可见课数、受限行仅元数据（`knowledge-sources-1793469839495945000.log`）+ invariant I-08 复核 | PASS |
| QA-BUG-006 多 confirmed 修订 occurrence 消失 | 同上测试 immutability 段：登记 revision_no=2 后旧修订 occurrence 仍在列表/详情且历史快照逐字节不变 | PASS |
| QA-BUG-007 + R-QA-008 范围校验 | 测试 exercise 关联段：paragraph 级 occurrence 对全部来源句同段校验；N-04 sentence scope 缺 paragraph 被 `3819 ck_occurrence_scope` 拒绝；N-05 非法组合 3819 | PASS |

## 3. 测试执行（全部绑定最终候选）

| 检查 | 退出码 | 日志 |
| --- | --- | --- |
| `KnowledgeSourcesIntegrationTest`（真实 MySQL） | 0 | `knowledge-sources-1793469839495945000.log` |
| `KnowledgeNormalizationIntegrationTest` + `KnowledgeConceptsTest` | 0（5/5） | `knowledge-normalization-1793468868902371000.log` |
| `negative_cases.sql`（N-01..N-15 适用项，含 N-01/02/03/04/05/07/09/10/13/14/15） | 0（全部按预期拒绝，逐行错误码见日志） | `knowledge-sql-negatives-1793469929467550000.log` |
| `invariant_checks.sql` 对账（孤儿 0、role/extra 0、I-07 撤回无新增、I-08 聚合一致） | 0 | `knowledge-invariant-checks-1793469941039597000.log` |
| HTTP 只读核心测试（/health、未知概念 404、概念列表、恢复副本读取） | 0 | `http-*`、`restored-*-final` 日志 |
| `QuizReportR1IntegrationTest`、`QuizScaleIntegrationTest`（10C-2-R1 参数化报告与 verifiedRun 回归） | 0 | `quiz-report-r1-1793469955528427000.log`、`quiz-scale-1793469971084564000.log` |
| `scripts` Python 单元测试 | 0 | `py-unit-tests-1793470008125343000.log` |
| Web `typecheck` / `lint` / `test` / `build` | 0 | `web-*-17934702*.log` |
| 迁移故障演练 V012_01–V012_07（DDL 中断、DML 回滚、history 异常，旧值逐格比对） | 0（7/7 PASS） | `migrations/fault-*-acceptance.json` |
| 备份恢复与重复启动（`data-transfer --phase10d` 行数+媒体哈希校验，恢复副本两次启动 012.07） | 0 | `restored-health-final`、`qa-restart-final-api.log`（私有）、备份目录 `backup-qa-final` |

命令、argv、cwd、HEAD、原始退出码与日志哈希逐条记录于 `docs/handoff/evidence/phase10d/execution-commands.jsonl`。

## 4. R-QA-009：运行账号权限（SHOW GRANTS 实证）

`northstar_app` 的 `SHOW GRANTS`（`grants-audit-1793469941435247000.log`）：无 `ALTER`、`DROP`、`TRIGGER` 及任何 DDL 权限；对知识表仅有 SELECT（浏览）与受控 INSERT（`attempt_knowledge`、`quiz_run_item` 等）；`attempt_knowledge`/`knowledge_concept_revision` 无 UPDATE/DELETE（N-13/N-14 实测 1142/45000）。迁移触发器的创建/重建仅由 `northstar_migrator`（带 TRIGGER 权限，用于测试夹具重建）执行，运行账号不涉及。**R-QA-009 关闭。**

## 5. R-QA-010 与 D02

概念复习 sources 接口尚未实现（无 concept_review 表与代码），**R-QA-010 维持 BLOCKED_BY_CORE**，不因 D01 通过而关闭。D02 全部条目 NOT VERIFIED，**10D 整体不得宣布通过，不得进入 10E**。

## 6. 失败原件与发现的新问题

1. 首次在修复候选上运行 `KnowledgeSourcesIntegrationTest` 失败（退出码 1，原件保留 `knowledge-sources-1793468862708745000.log`）：负例夹具的 sentence-scope 插入未带 `paragraph_id`，被收紧后的 `ck_occurrence_scope` 拒绝；且 `cleanup()` 会 DROP 迁移级触发器（含 V012_01/07 新增 4 个）而 `recreateTriggers()` 不重建。**CORE 的修复记录声称的"复跑集成测试"未真正完成。**
2. QA 侧在隔离构建副本（非冻结候选文件）中做了测试夹具适配：为 oc-fk-s1/s2 补 paragraph 参数；recreateTriggers 增补 4 个迁移触发器。冻结候选源码未改动。适配后的夹具运行通过（§3 第一行）。
3. 失败期间重建测试库一次（prepare-tests）；全部后续验证在新库上进行。探针/失败库按约定保留未清理。

## 7. 数据库前后对账与目标保留

1. 迁移故障演练 7/7：失败后 history 未变、旧表逐格一致（`fault-*-acceptance.json`）。
2. 备份恢复：源导出→新库逐表行数一致、媒体哈希一致；恢复副本含全部 46 条迁移与 4 个不可变触发器（`final-target-identity.json`）。
3. 保留目标：`northstar_phase01_test`（含 QA 种子与负例残留）、`northstar_restore_20261031234422`、`northstar_restore_20261101024700`、`northstar_restore_20261101021230`。测试服务已全部停止，8176 已释放。

## 8. 结论与候选提交前置条件

1. 七项缺陷修复在数据库层与运行层均复验通过；规范化、HTTP、回归、迁移故障、备份恢复、权限边界全部通过。D01 复验 **PASS**。
2. **前置条件（P2，阻塞候选提交）**：CORE 必须把 §6.1 的测试夹具适配落入候选（negativeFixture 补 paragraph、recreateTriggers 重建 4 个迁移触发器），并复跑集成测试至绿色后才能提交候选；未适配前候选自带测试套件为红。
3. R-QA-010 与 D02 维持 BLOCKED_BY_CORE；未开始 10D-2，未提交/合并/部署，未修改个人学习库。

## 9. 前置条件关闭（2026-11-01 合并部署前补记）

用户批准合并部署后，QA 夹具适配已落入冻结候选（`KnowledgeSourcesIntegrationTest.java` 两处修改，业务代码零改动），并在重建的隔离测试库复跑：`knowledge-sources-final-1793508550777035000.log` 退出码 0，1/1 通过。§8.2 前置条件关闭。
