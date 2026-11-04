> 2026-11-02 最新独立复测：P1受限分页500及合法游标422已关闭，本次定向PASS，阶段整体CONDITIONAL PASS。新JAR771a72e8…，冻结336项输入；独立3374库7/7集成回归、原3364库只读59表哈希及真实Playwright通过。详见 [最新复测报告](10D_D02_QA_P1_RETEST.md) 与 [最终验收状态](10D_D02_QA_FINAL_ACCEPTANCE.md)。以下保留历史记录，不以旧候选结果替代新候选未测项。

# Phase 10D-D02 QA 缺陷报告

日期：2026-11-01（Asia/Shanghai）。QA-EXEC 第一轮已完成（QA 隔离容器 `northstar-qa-d02-20261101`，MySQL 8.4.9，127.0.0.1:3348，schema `northstar_phase01_test`，server_uuid `c9899036-d5d2-11f1-a04e-4a84c4080faa`）。以下缺陷均已实测复现，原始日志见 `qa/phase10d2/evidence/`。

## 1. 缺陷登记

| Bug ID | 等级 | 类型 | 复现（最小） | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| QA-D02-BUG-001 | **P1（阻断）** | 业务 | 概念首个真实错误作答（reading/dictation 均可）：`ConceptReviewSources.record` 执行 `INSERT INTO concept_review_card(id,concept_id)`，而 V012_09 中 `prompt_kind`/`protocol_version` 为 NOT NULL 且无默认值 → SQL 1364 → 首个错误无法建卡，D02 主链路断裂 | `qa-d02-mvn-run6.log`（错误码 1364 全栈）；失败后 DB 对账 0 卡 0 来源 0 attempt（事务原子回滚成立） | **待 CORE 修复**（建议：INSERT 显式补 `'meaning_recall','concept_review_v1'`） |
| QA-D02-BUG-002 | P3 | 业务 | 同上场景：确定性约束失败被统一映射为 `503 DATABASE_UNAVAILABLE` 且 `retryable:true`，误导客户端无限重试 | `qa-d02-mvn-run6.log` 响应体 | 待 CORE 修复 |
| QA-D02-BUG-003 | P2 | 测试（CORE 自测） | `ConceptReviewIntegrationTest` 在 `exercises()` 之前调用 `registerA/registerB`；登记 CLI 要求 `exercise` 行已存在 → 422 `KNOWLEDGE_CONTEXT_MISMATCH`，自测无法启动 | `qa-d02-mvn-run4.log`；D01 同套件先 `exercises()` 后 register（`KnowledgeSourcesIntegrationTest:49/328` 对照） | 待 CORE 修复 |
| QA-D02-BUG-004 | P2 | 测试（CORE 自测） | `cleanup()` 先删 attempt 的 `command_receipt` 再删 attempt（FK 1452），且未清理 `study_stage`（删 sentence 时 FK 1452）；finally 异常掩盖主体失败 | `qa-d02-mvn-run8.log`、`qa-d02-mvn-run12.log`、`run14-final-db-state.txt` | 待 CORE 修复 |
| QA-D02-BUG-005 | P2 | 测试（CORE 自测） | replay 场景使用**新** eventId 且每次重新生成 `clientOccurredAt`：回执哈希覆盖完整 payload → 同 event 必 409 而非重放；改为相同 body 后，新 eventId 首发本身产生新来源，与 `sources==3` 期望矛盾（实测 expected 3 but was 4），`attempt_knowledge==3` 断言亦与场景不符。期望体系自相矛盾，自测不能作为 D02 门禁 | `qa-d02-mvn-run10.log`（409）、`qa-d02-mvn-run14.log`（expected 3 but was 4）、`run14-final-db-state.txt`（4 条来源逐行回链） | 待 CORE 修复 |

等级定义：P0 来源泄露/跨概念关联/CAS 丢更新/错误成绩生成/旧学习记录改变；P1 功能断裂；P2 边界/一致性缺陷；P3 观察项。

## 2. 诊断构建披露（不构成 CORE 候选通过依据）

为继续探查链路，QA 在隔离 worktree 构建了诊断变体，差异仅两类且未改任何断言预期：① BUG-001 的 INSERT 补两列；② 自测夹具顺序/cleanup 顺序/replay 相同 body 三处 harness 修复（完整差异存档 `evidence/ConceptReviewIntegrationTest.qa-diag.java.txt`）。诊断构建下实证：V012.09–V012.11 经 Flyway 正常应用；跨课同概念错误追加同一张卡；来源行全部回链真实 attempt/occurrence/concept；相同 body 重放返回同一 attemptId 且不重复入库；复合 FK 拒绝跨概念/跨卡来源写入（CORE 自测 sqlNegatives 断言通过）。诊断后候选文件字节已恢复并复验（test=`2e7ce8f5…`、Sources=`979348e4…`，与 `qa-candidate-baseline-sha256.txt` 一致）。

## 3. 处置要求

CORE 修复 BUG-001/002（业务）并在新候选上修复 BUG-003/004/005（自测）后，由 QA 重跑测试计划 §4 全部矩阵。本轮未发现来源泄露、跨概念关联、CAS 丢更新、错误成绩生成或旧学习记录改变——但相关矩阵条目尚未执行到（被上述缺陷阻断），不能据此宣布通过。
