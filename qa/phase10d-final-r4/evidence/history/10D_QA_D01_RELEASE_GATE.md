# Phase 10D-D01 最终发布门禁整改报告

日期：2026-11-01（Asia/Shanghai）。结论：**D01 发布门禁 PASS（附条件见 §7）**。冻结候选 = Git HEAD `a5084cb` + 本轮未提交整改（92 个文件逐文件 SHA-256 见 `qa/phase10d/evidence/candidate-sha256.txt`，清单哈希 `d90dfbc122300e10b3c70065a6e0349afd818161ba42f6460c9e2cd6c66fac36`）。所有验证在冻结候选主 checkout（`run-tests-main`，cwd=仓库根）与专用隔离容器 `northstar-phase10c2-20261031d-*`（3339/3340/3341–3347 回环）完成；个人库 3308、个人服务 3100/8085、现有 MySQL 卷全程未连接、未触碰。未提交、未合并、未部署、未开始 10D-2/10E。

## 1. 任务一：测试夹具同步与候选复跑

1. 与 QA worktree `test/10d-qa`（ff0dbe1 基线）逐字比对确认：CORE 候选已包含两项夹具修正——`negativeFixture` 的 oc-fk-s1/s2 sentence-scope 插入已带合法 `paragraph_id`（CV+"-p1"，与 fixture(C,1,2,…) 的段落分配一致）；`recreateTriggers()` 已重建 V012_01/V012_07 的 4 个不可变触发器（knowledge_revision_no_update/no_delete、attempt_knowledge_no_update/no_delete），定义与迁移原文逐字一致。差异恰为这两处修正，无其他漂移。
2. 最终候选上复跑（全部在主 checkout 执行，非临时副本）：
   - `KnowledgeSourcesIntegrationTest` 退出码 0（`knowledge-sources-gate-1793519053350996000.log`）；
   - `KnowledgeNormalizationIntegrationTest` + `KnowledgeConceptsTest` 退出码 0（`knowledge-normalization-gate-1793519059796546000.log`）；
   - `QuizScaleIntegrationTest` + `QuizReportR1IntegrationTest` 回归退出码 0（`quiz-regression-gate-1793519062944788000.log`）。
3. 两次失败原件保留：首次复跑因容器重启后 `log_bin_trust_function_creators` 复位，cleanup 阶段 1419（`knowledge-sources-gate-1793518755000019000.log`）；按迁移原文重建全部 24 个迁移级触发器并核数后恢复（`restore-triggers2-1793518840801204000.log`、`trigger-count-1793518841132234000.log`）。规范化套件因共享测试库历史 QA 残渣计数失败一次（`knowledge-normalization-gate-1793518929003700000.log`）→ 按 D01 复验既有方法论用 `prepare-tests` 重建 `northstar_phase01_test`（含 V012_08）后全绿。测试必须先于负例 SQL 执行（负例残留会污染计数断言），已写入 §6。

## 2. 任务二：概念与修订关联负例（R-QA-011）

1. 迁移前实证：在 012.07 隔离测试库自建两个概念 qa8-con-a/qa8-con-b 及修订 qa8-rev-b，插入 `concept_id=qa8-con-a, revision_id=qa8-rev-b` 的 lesson-scope occurrence——**成功**（`prefix-probe-1793518215240716000.log` 输出 CROSS_CONCEPT_INSERT_SUCCEEDED）。单列外键 `knowledge_occurrence_ibfk_2` 确实不校验同概念性；`prestate-*.log` 的 SHOW CREATE TABLE 为缺陷留档。
2. 数据库级保护：新增迁移 `V012_08__occurrence_revision_integrity.sql`——`knowledge_concept_revision` 增加 `uq_revision_id_concept(id, concept_id)` 唯一索引，`knowledge_occurrence` 增加复合外键 `fk_occurrence_revision_concept(revision_id, concept_id)` 引用之。未修改 V012_01–V012_07 任何历史迁移，未执行 repair。
3. 应用路径均为真实 Flyway：测试库经 serve 启动应用（health 返回 012.08）；正式目标 schema 经两条隔离路径重建后应用（§4）；恢复副本经 data-transfer 结构 dump 携带（`poststate-*.log` 含新外键与索引实证）。
4. 修复后负例：`qa/phase10d/sql/negative_cases.sql` 新增自包含 N-17（不依赖 QA 种子），实测 `1452 fk_occurrence_revision_concept`、`cross_inserted=0`（`negative-cases-final-1793519093283881000.log`）；`KnowledgeSourcesIntegrationTest.sqlNegatives()` 新增跨概念负例（kn-fk 配 rv-bank-fin），随套件通过。对账新增 I-11（cross_concept_occurrences=0，`invariant-checks-final-1793519093615848000.log`）。

## 3. 任务三：权限边界（SHOW GRANTS 按 schema 区分）

账号级与连接级证据：`grants-accounts-1793519871593760000.log`（3340 容器）、`grants-fault-ddl-*.log`、`grants-fault-07-*.log`（故障演练容器，采集后已停止）。

| Schema 类别 | northstar_app | northstar_migrator | 额外权限来源与清理策略 |
| --- | --- | --- | --- |
| 正式运行目标 `northstar_english`（3340） | schema 级 SELECT + 运行写表受控 INSERT/UPDATE；**无任何 DDL**（无 CREATE/ALTER/INDEX/DROP/TRIGGER/REFERENCES） | 全套 DML+DDL+TRIGGER（迁移需要） | 由容器 init 与迁移流程授予；无需清理 |
| QA 测试库 `northstar_phase01_test` | 与正式目标一致，另加 7 张知识登记表 INSERT/UPDATE/DELETE | 同上 | 来源 `scripts/phase10d_isolated.py` `prepare-tests()` 夹具授权；仅存在于隔离测试库，重建即清零 |
| 恢复演练库 `northstar_restore_*` | SELECT + 恢复工具按表授予的受控写权限 | 全套 DML+DDL+TRIGGER（结构 dump 需建表/触发器） | data-transfer `restore` 尾部授予；随 schema 删除消失 |
| 故障演练库（fault-ddl…fault-07 容器） | 同正式目标窄权限（实测无 DDL） | migrator 同上；fault_migrator 有 ALTER/TRIGGER（故障注入需要） | 演练容器自带 init 账户；容器/卷可整体处置 |
| 探针库 `northstar_restore_20261101024700`、`qa_flyway_probe` | 宽权限（含 ALTER/TRIGGER） | 同 | 历史 QA 探针遗留；库本身可丢弃，删除 schema 即回收权限 |

正式运行账号无非必要 DDL 权限，结论与 D01 复验 §4 一致且本轮未放宽。

## 4. 隔离迁移与恢复检查

1. **发现并处置陈旧字节库**：3339/3340 两个容器的 `northstar_english` 均为 QA 修正前字节所建，Flyway validate 对 012.01/02/04/07 报校验和不一致（原始日志保留于 `.local/phase10d/database/logs/17-1793519112376238000-upgrade-flyway-None.txt` 等）。按冻结纪律不做 repair，重建两个 schema 后用最终候选字节重跑：
   - upgrade 路径（3339）：固定旧备份恢复 → 010.06 基线逐格比对 → 迁移至 012.08 → 两次重启快照一致（`migrations/upgrade-acceptance.json` PASS）；
   - empty 路径（3340）：全新空库初始化至 012.08 + 演示内容初始化 → 两次重启快照一致（`migrations/empty-acceptance.json` PASS）。
2. 备份恢复：`data-transfer --phase10d` 备份 PASS；恢复首跑失败（错误 3105：备份负载含 `knowledge_occurrence.location_guard` 生成列），暴露上轮未覆盖的恢复缺陷——上轮备份恰好无 occurrence 行所以漏过。已修复 `scripts/data-transfer.py`：恢复列集从 information_schema 动态剔除全部 STORED GENERATED 列（替换原 version_sentence_map 单表特判）。重跑恢复 PASS：逐表行数与媒体哈希一致，恢复副本 `northstar_restore_20261101075705` 两次启动 health 012.08、`/knowledge/concepts` 只读探测正常（`restored-health-gate.log`、`restored-concepts-gate.log`）。三个失败半成品目标 `northstar_restore_20261101075428/075528/080015` 按约定保留未清理。
3. `scripts` Python 单元测试 18/18 OK（含 data-transfer 白名单新增 012.08）。

## 5. 冻结清单

92 个文件（原 89 文件候选 + V012_08 + 2 个 QA SQL），重新逐文件 SHA-256 冻结；清单哈希 `d90dfbc122300e10b3c70065a6e0349afd818161ba42f6460c9e2cd6c66fac36`。本轮修改文件：V012_08（新增）、`KnowledgeSourcesIntegrationTest.java`、`negative_cases.sql`、`invariant_checks.sql`、`phase10d_isolated.py`、`data-transfer.py`、两份清单文件。业务 Java 主代码零改动。

## 6. 运行顺序约定（本轮实证）

1. 共享隔离测试库上：`prepare-tests` → 知识/quiz 测试套件 → SQL 负例 → 对账。负例与探针会留下不可删除的 append-only 残渣，后置执行。
2. 容器重启后必须重设 `SET GLOBAL log_bin_trust_function_creators=1`（migrate()/prepare-tests 流程已内置，手工触发器操作前需补设）。
3. `snap()` 快照按 tag 缓存：跨版本重跑必须换新 tag（本轮 `v01208`/`first-start-01208`/`second-start-01208` 已固化为参数化 tag）。

## 7. 结论与边界

1. 七项 D01 缺陷修复维持 PASS；R-QA-011（跨概念修订关联）以 V012_08 数据库级保护关闭（迁移前可插入实证 + 修复后 1452 负例 + I-11 对账）。**D01 发布门禁 PASS。**
2. 附条件：`scripts/deploy-phase10d.py` 的目标版本仍为 012.07，下一轮部署前必须随候选同步（本轮未授权部署，未改动）；`scripts/tests` 5 个用例在沙箱内因 `ps`/socket 受限误报，沙箱外 OK。
3. R-QA-010（conceptReviews）维持 BLOCKED_BY_CORE；D02 全部条目 NOT VERIFIED，10D 整体不得宣布通过，不得进入 10E。
4. 保留物：3 个失败恢复目标、QA 探针库、失败测试日志原件；未清理任何失败现场。未修改个人学习库；未自动提交/合并/部署。
