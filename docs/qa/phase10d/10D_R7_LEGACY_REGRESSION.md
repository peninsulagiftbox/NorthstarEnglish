# Phase 10D-QA R7 历史兼容回归

日期：2026-11-04（Asia/Shanghai）。结论：**关键回归部分通过；确认一个 P1 缺陷。**

## 通过项

| 范围 | 结果 | 证据 |
| --- | --- | --- |
| 知识规范化独立库 | PASS，1/1 | `qa/phase10d-final-r7/evidence/suite_normalization/r7-normalization.log` |
| 10C-1 音频关键回归 | PASS，5/5 | `qa/phase10d-final-r7/evidence/suite_audio/r7-audio.log` |
| 10C-2 Quiz 原子性 | PASS，2/2 | `qa/phase10d-final-r7/evidence/suite_quiz_atomic/r7-quiz_atomic.log` |
| 3397 恢复后续学、幂等、重启 | PASS | `qa/phase10d-final-r7/evidence/r7-recovered-study-result.json` |
| 旧 Demo 浏览器播放、切句、暂停、刷新恢复 | PASS，两条媒体响应 206 | `qa/phase10d-final-r7/evidence/r7-browser-demo-result.json` |
| Node test/typecheck/lint/build | 退出码 0 | `qa/phase10d-final-r7/evidence/node-*.log` 与 `web-identity.json` |

浏览器 BUILD_ID 为 `mB0BX6ovaStArA61zmdDR`；四套 Java 集成回归均使用独立容器和独立 UUID，日志内绑定候选清单。

## 确认缺陷

- **P1：`review_result` 缺少 UPDATE 保护。** `QuizReviewIntegrationTest.completeRunsEvidenceKnowledgeCardsCasIdempotencyAndRestart` 期望 UPDATE 抛出 `DataAccessException`，实际 UPDATE 成功。失败断言在测试第 79 行，日志为 `qa/phase10d-final-r7/evidence/suite_quiz_review/r7-quiz_review.log:79`。
- 最小复现：在新建隔离库中先插入一条 `review_result`，再执行 `UPDATE review_result SET rating='again' WHERE event_id='<已插入 event_id>';`。当前没有 `review_result_no_update` 触发器，语句成功；`concept_review_result` 已有对应触发器，`review_result` 没有。
- 影响：旧句卡自评历史可被数据库端修改，违反“学习结果只追加/不可变”契约。未观察到 API 层修改路径。
- 处置：本 QA 轮不改业务代码；需 CORE 在正式迁移或新迁移中补齐与 `concept_review_result` 一致的 append-only 触发器，并用真实集成测试复验。

## 失败与无效运行

- 首次 20 套件混合运行因共享数据库污染和 `NORTHSTAR_AUDIO_FIXTURES` 缺失失败；原始日志保留在 `qa/phase10d-final-r7/evidence/regressions/r7-d01-legacy-audio-integration.log`。该运行不判产品缺陷。
- 随后改为逐套件独立数据库：quiz_review 的失败仍稳定复现，其余三套通过。
- 浏览器前两次脚本失败因定位器和响应状态断言过严；最终脚本使用音频 readyState 与真实媒体响应判定，原失败输出未被覆盖。

## 2026-11-05 修复复验

- 新增 V012.12 `review_result_no_update` 触发器后，`QuizReviewIntegrationTest` 在全新隔离容器通过。
- 修复目标数据库 UUID：`fdbae911-d868-11f1-ac49-22f976e3a644`；迁移到 012.12，触发器为 `review_result_no_update / UPDATE`。
- 结果：`qa/phase10d-final-r7-fix/evidence/p0p1-fix-result.json`；日志：`qa/phase10d-final-r7-fix/evidence/p0p1-quiz-review.log`。
