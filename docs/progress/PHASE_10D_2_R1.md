# Phase 10D-2-R1 定向修复报告

日期：2026-11-01 · HEAD：a5084cb（基线未改） · 状态：修复完成，等待 10D-QA 独立复测

## 一、改动文件

本轮 R1 直接修改（此前 10D-2 候选之上）：

- `apps/api/src/main/java/local/northstar/exercise/ConceptReviewController.java`：rating 请求体语义校验（未知 rating / 未翻卡）移到数据库状态检查之前，避免非法输入被"未到期"409 掩盖；修复 `due` 分页 `cardCursorKey` 把 UUID 卡 id 当数字解析导致的 500。
- `apps/api/src/test/java/local/northstar/knowledge/ConceptReviewIntegrationTest.java`：`rating()` 改用固定 `clientOccurredAt` 使同 eventId 重放 payload 字节一致；BUG-002 负例计数排除自插的 `cr-pre` fixture 行；`concurrent()` 预期改为"只有一个 CAS 赢家"（1 条结果、row_version+1、reps=1）。
- `apps/api/src/test/java/local/northstar/knowledge/KnowledgeSourcesIntegrationTest.java`：D01 cleanup 补删 D02 自动建卡产物（`concept_review_source`/`concept_review_result`/`concept_review_card`），顺序先子后父。

连同上一轮已完成的五项缺陷修复（`ConceptReviewSources.java` 建卡 INSERT 补 `prompt_kind='meaning_recall'`、`protocol_version='concept_review_v1'`；`ApiProblems.java` 确定性约束错误返回 500 `DATA_CONFLICT` 非重试；Fixture 顺序/清理/重放语义修复；V012_09 加 `uq_concept_card_identity`、V012_10 FK 改为 `(card_id,concept_id)`），全部候选文件见冻结清单。

## 二、关键设计决定

1. BUG-001 修复值与卡片协议一致：`prompt_kind='meaning_recall'`、`protocol_version='concept_review_v1'`，与调度（`simple_v1`）及 `due` 查询返回字段一致；未放宽 NOT NULL、未改已执行迁移。
2. BUG-002 不把全部 SQLException 转 422/409：暂态 → 503 retryable；确定性约束 → 500 `DATA_CONFLICT` retryable=false；其余 → 500 `INTERNAL_ERROR`。SQL 细节不外泄，内部保留 ERROR 日志与 traceId。
3. `due` 分页 cursor 第二段是 UUID 卡 id（正则 `[0-9]+:[0-9a-fA-F-]{36}`），原实现 `Long.parseLong` 在 limit 命中 `rows.size()==size` 时必然 500，属真实业务缺陷，按契约修复为字符串拼接。
4. 冻结清单排除两个清单文件自身（自引用哈希不可构造），清单完整性由 `candidate-filelist-sha256.txt` 中的清单哈希保证，`qa/phase10d2/tools/verify-candidate.sh` 独立校验。

## 三、运行命令与结果（全部在专用隔离库，未触碰个人库 3308 与已部署服务）

| 验证 | 命令 | 结果 |
|---|---|---|
| 1364 原样复现 | 隔离测试库 `INSERT INTO concept_review_card(id,concept_id,owner_key)...`（事务内） | `ERROR 1364: Field 'prompt_kind' doesn't have a default value`，已回滚、0 行残留 |
| 双路径迁移 | `python3 scripts/phase10d_isolated.py migrations`（重建容器/卷后） | upgrade 与 empty 均 PASS，`targetVersion=012.11`，两次启动快照一致 |
| 测试库重建 | `python3 scripts/phase10d_isolated.py prepare-tests` | PASS（`northstar_phase01_test`@012.11） |
| D02 全量 | `... run-tests-main r1test9/r1final apps/api/mvnw ... -Dtest=ConceptReviewIntegrationTest` | PASS（Tests run: 1, Failures: 0, Errors: 0） |
| D01 回归 | `... run-tests-main r1reg2 ... -Dtest=KnowledgeSourcesIntegrationTest` | PASS |
| 10C-2-R1 回归 | `... run-tests-main r1reg3 ... -Dtest=QuizScaleIntegrationTest,QuizReportR1IntegrationTest` | PASS（3+2 用例） |
| Java 打包 | `JAVA_HOME=.local/jdk21/... apps/api/mvnw -f apps/api/pom.xml package -DskipTests` | JAR SHA-256 `cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb` |
| Node | `apps/web`: `typecheck` / `lint` / `test` / `build` | 全部通过（lint 有 1 个既有 warning：`KnowledgeConcepts.tsx` 未用变量；构建 ID `almrGkLOMhLOTdxWQBx_i`） |
| Python | `python3 -m unittest discover -s scripts/tests` | 18/18 OK |
| 冻结校验 | `sh qa/phase10d2/tools/verify-candidate.sh` | PASS：27 个候选文件字节一致，清单哈希 `087f849df28d66d1c80d48e5328322c3c385c152ea3ea65313e87b5f4703b787` |

中途失败日志（保留为审计证据）：`docs/handoff/evidence/phase10d/concept-review-r1{,b,c,d}-*.log`（上一轮：并发建卡 MVCC 盲区、`LAST_INSERT_ID` 截断）、`r1test*.log`（重放 payload 不一致、校验顺序、分页 500）、`r1reg1-*.log`（D01 清理被 D02 新 FK 阻塞）。最终成功日志：`r1final-1793529476868179000.log`、`r1reg2-*.log`、`r1reg3-*.log`。迁移验收证据：`docs/handoff/evidence/phase10d/migrations/{upgrade,empty}-acceptance.json`（上一版本已备份至 `pre-r1-backup/`）。

## 四、验收条目

- 通过：BUG-001 建卡（复现 1364 → 修复后全生命周期成功）；BUG-002 HTTP 负例（预插冲突行 → 500/DATA_CONFLICT/retryable=false，失败事务不留 receipt 与结果）；BUG-003/004 夹具顺序与清理（含 D01 测试新增的 D02 子表清理）；BUG-005 幂等（同 eventId 同 payload 重放、异 payload 409、新 eventId 新命令，attempt_knowledge 断言 1）；两课同 Concept 多来源（4 来源 1 卡）；来源跨 Concept/Version 负例；并发建卡收敛 1 卡 2 来源；CAS 成功/冲突/并发单赢家；自评不进客观成绩；复习来源权限正反例；review_item/review_result 保护；D01 关联与 V012_08 完整性回归；10C-2-R1 测验与报告回归。
- 未通过：无。

## 五、数据库前后对账（最终运行后，隔离测试库）

`concept_review_card=0`、`concept_review_source=0`、`concept_review_result=0`、`attempt_knowledge=0`；残留 `command_receipt=7`、`exercise_attempt=4` 属 demo 内容与 QuizScale 夹具，与 D02 无关。

隔离库身份：容器 `northstar-phase10c2-20261031d-empty`，MySQL 8.4.9，`127.0.0.1:3340`，server_uuid `be2214aa-d5dd-11f1-9492-7e28170bc077`，验收库 `northstar_english` / 测试库 `northstar_phase01_test`。Flyway checksum（`northstar_english`）：012.08=614772575、012.09=-1897723092、012.10=1214340811、012.11=747985570，与当前工作区 SQL 一致。

## 六、未解决问题 / 未验证项

- CORE 自测全绿仅代表可重新提交 QA-EXEC；独立 QA 复测未进行。
- 浏览器端复习页手工验证未做（本轮无 UI 改动逻辑，仅回归构建）。
- 未提交、未合并、未部署；V012_08 及更早迁移为冻结基线（HEAD a5084cb）未改动。
- 上一轮 `phase10d2` 旧清单因自引用哈希必然漂移，本轮按"清单排除自身"方案重新冻结（已在报告与清单头部注明）。

## 七、下一阶段依赖

等待 10D-QA 独立复测本候选（`qa/phase10d2/evidence/` + `output/review/northstar-phase10d2-r1-sanitized-evidence.zip`）；复测通过前不进入 10E。

证据包：`output/review/northstar-phase10d2-r1-sanitized-evidence.zip`（SHA-256 `842696acbfeb42ad0bf5ff61fa716e1740d652c4f6a57432b12559b0646575ac`，23 个文件，已扫描确认不含凭据/个人记录/录音/教材内容）。
