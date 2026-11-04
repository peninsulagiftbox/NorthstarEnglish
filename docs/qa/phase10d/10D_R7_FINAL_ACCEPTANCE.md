# Phase 10D-QA R7 最终封版验收

日期：2026-11-04（Asia/Shanghai）。结论：**PHASE 10D NOT READY — NO-GO TO 10E。**

## 已通过

1. 用户确认 M06–M08 建议映射后执行；初始 399 项候选无漂移。
2. D01-M03.b 和 D01-M03.c：真实 Flyway DML 回填失败、history 登记失败、重启阻断、故障前备份在新目标恢复均通过。
3. D01-M04 / D01-M05 / 建议 M06：3397 独立容器与卷恢复 59 表、生成列、非空录音一致，恢复后真实续学、幂等和重启通过。
4. 建议 M07 预检：截断备份、校验和错误、非空录音缺失均在创建目标前拒绝。
5. 建议 M08 关键项：知识规范化、音频、Quiz 原子性、旧课浏览器播放/切句/刷新恢复通过。
6. Node test/typecheck/lint/build、Java五套初始回归和 B08/B09 既有证据仍在同一冻结候选链上。

## 阻塞项

| 等级 | 问题 | 影响 |
| --- | --- | --- |
| **P0** | `data-transfer.py restore` 在备份目录缺少 `COMPLETE` 时仍返回 PASS 并创建新 schema。 | 不完整备份可被标记为恢复成功，可能造成不完整目标被投入使用。 |
| **P1** | `review_result` 缺少 UPDATE 保护触发器。 | 旧句卡自评历史可被数据库端修改，违反不可变学习证据契约。 |
| 门禁 | D01-M03.a 未验证。 | 不能宣布 D01-M03 全量通过。 |
| 门禁 | M07 的备份过程、恢复过程、媒体复制中断和 API 失败可诊断性未验证。 | 中断安全仅覆盖部分场景。 |
| 门禁 | D01 全量历史回归、完整旧 Demo 学习闭环与 10C-2 全量回归未在 R7 重跑。 | 建议门禁 M08 不能记全量 PASS。 |

`COMPLETE` 最小复现：复制有效备份目录后删除 `COMPLETE`，对 `learning.json` 调用原版 `data-transfer.py restore`。实测返回 PASS 并创建 `northstar_restore_20261104133432`。证据为 `qa/phase10d-final-r7/evidence/r7-backup-faults-result.json`；前三类损坏均正确拒绝。

`review_result` 最小复现见 `10D_R7_LEGACY_REGRESSION.md`。两项均不在本轮修改业务代码。

## NOT VERIFIED

- D01-M03.a 多语句 DDL 进程终止。
- M07 备份过程、恢复过程、媒体复制中断、DB/媒体不一致和 API 启动失败可诊断性。
- D01 全量历史回归、旧 Demo 完整闭环、10C-2 全量历史分母与 JDBC 报告查询重跑。
- 实体麦克风/设备验收；不在本轮浏览器 MediaRecorder 覆盖范围。

## 证据与部署

- 五份 R7 报告、阶段报告、完整候选补充清单和脱敏 ZIP 由本轮生成。
- 完整候选清单：`qa/phase10d-final-r7/evidence/qa-r7-final-candidate-complete.sha256`，418 项；初始 399 项和 19 项补充均校验通过。
- 脱敏证据包：`output/review/northstar-phase10d-r7-final-sanitized-evidence.zip`，799 个文件；独立解压后 `verify_evidence.py` 校验 799/799 PASS。
- 本轮未修改 CORE、未修改已执行迁移、未提交/推送、未部署个人环境、未操作个人 3308/3100/8085。
- 3385 源库与所有 R7 隔离目标、故障现场、3389 首套无效前置条件保留，未删除。

**PHASE 10D NOT READY — NO-GO TO 10E**

## 2026-11-05 P0/P1 修复补充

- **P0 已修复**：`data-transfer.py` 在 restore 路径加入 `COMPLETE` 预检；备份目录缺少标记、标记不是文件或内容与 JSON SHA-256 不一致时，在任何目标创建前拒绝。
- **P1 已修复**：新增 V012.12 `review_result_no_update`，阻止 UPDATE。`QuizReviewIntegrationTest` 在全新隔离容器通过，确认期望的 `DataAccessException` 现在发生。
- 验证证据：`qa/phase10d-final-r7-fix/evidence/p0p1-fix-identity.json`、`p0p1-fix-result.json`、`p0p1-quiz-review.log`、`p0p1-history.log`、`p0p1-review-result-triggers.log`；单元证据在 `qa/phase10d-final-r7-fix/evidence/p0p1-data-transfer.log`。
- 结论仍为 **NO-GO TO 10E**：剩余 M03.a、M07 未执行中断场景、D01 全量历史回归、旧 Demo 完整闭环和 10C-2 全量重跑仍未关闭。

## 2026-11-05 剩余门禁收口（全部在隔离环境执行）

### D01-M03.a V012.02 多语句 DDL 边界进程终止 — PASS

1. 注入：全新容器 `northstar-qa-final-r7-fault-ddl2-20261104`（3395，独立卷/UUID）迁移到 012.01 后，另一会话 `LOCK TABLES knowledge_concept WRITE` 阻断第二条语句；检测到 Flyway 会话处于 `Waiting for table metadata lock` 的 `CREATE TABLE knowledge_occurrence` 后，先对服务端会话执行 `KILL`，再对 JVM `SIGKILL`。语句 1（`ALTER TABLE sentence ADD UNIQUE KEY uq_sentence_paragraph`）已提交、语句 2 未提交、history 无 012.02、旧行逐值不变。证据：`qa/phase10d-final-r7/evidence/fault_ddl2/m03a-inject-result.json`、`m03a-probe-samples.json`、`inject.log`。
2. 重试阻断：重跑 Flyway 以 MySQL 1061（duplicate key name）失败，history 记录 `012.02 success=0`，`knowledge_occurrence` 仍不存在，不可能误判成功。证据：`m03a-retry-result.json`、`retry.log`、`retry-2.log`。
3. API 启动失败可诊断性：对故障目标启动完整 API（默认 target），进程退出码 1、/health 从未返回 200、日志含 1061 诊断信息。证据：`m07-api-failure-result.json`、`api-failure.log`。
4. 恢复：故障前基线备份（mysqldump，SHA-256 见 `pre-fault-backup.json`）导入新容器 `northstar-qa-final-r7-fault-recovery-ddl-20261104`（3398，独立卷/UUID），迁移至 012.11，API 读取旧课、提交听写 attempt、同 eventId 重放回执一致，旧行不变。证据：`m03a-recovery-result.json`。故障目标原样保留。

### R7 建议 M07 中断安全 8/8 — PASS

原 4 项（截断备份、校验和错误、非空录音缺失、缺 COMPLETE，见 `r7-backup-faults-result.json`）加上本轮 4 项（`r7-m07-interruption-result.json`，源库前后逐值一致）：

1. 备份过程中断：备份目录刚创建即 SIGKILL，无 COMPLETE；restore 以退出码 1 拒绝且未创建任何目标 schema；换新目录重试备份 PASS。
2. 恢复过程中断：目标 schema 仅 1 张表时 SIGKILL，关键表缺失（源 lesson=4/attempt=12/recording=1），无媒体目录；同一备份恢复到新目标 PASS 且行数与源一致。
3. 媒体复制中断：进入媒体复制阶段即 SIGKILL（流程未输出 PASS）；重试目标媒体文件数与清单一致。
4. API 启动失败可诊断性：见 M03.a 第 3 步（同一证据）。

### R7 建议 M08 兼容回归 — PASS

1. 全量历史回归（含 D01 知识套件、10C-2 Quiz 分母/复习/报告 JDBC 查询、音频、目录、P1 不可变断言与 V012.12 迁移）：ROOT 全部测试分两组在全新隔离容器运行，46/46 + 1/1 全部通过。证据：`qa/phase10d-final-r7/evidence/suite_full5/r7-full5.log`（46 项 BUILD SUCCESS）、`suite_full6/r7-full6.log`（1 项 BUILD SUCCESS）。
2. 旧 Demo 完整学习闭环：未修改的 `scripts/full-learning-loop.js` 经固定版本 Playwright CLI 在 3397 M06 完整恢复目标上执行，7 项检查全部通过（含真实听写错误→复习链路、写作版本、Quiz 提交、草稿刷新、无 AI 标记）。证据：`r7-demo-loop-result.json`、`demo-loop-run-code.log`、截图 `output/playwright/phase10b2-demo/`。

### 过程发现（记为 QA/产品观察，不阻塞本验收）

1. **恢复副本授权矩阵缺口（P2，待产品决策）**：`data-transfer.py` 恢复授权不含 `knowledge_concept`、`knowledge_concept_revision`、`knowledge_occurrence`、`exercise_sentence`、`exercise_knowledge`、`knowledge_projection`、`legacy_knowledge_link` 的写权限；知识注册 CLI 在恢复副本上会被拒。本轮按"学习者最小授权 + 知识注册维护授权"的组合在回归容器验证测试，未修改恢复工具契约。
2. **套件隔离缺陷（P2）**：`MultiCourseIntegrationTest` 无 cleanup 且复用 `fixture-a/b`；surefire 按全类名排序时先于 `KnowledgeSourcesIntegrationTest` 运行会污染其夹具，共享容器全量必然冲突。本轮以两组隔离运行收口，属测试基建问题，不计产品缺陷。
3. **首轮注入的意外观察**：JDBC `socketTimeout=3000` 不会中止服务端被 MDL 阻塞的 DDL——驱动放弃后，锁释放时挂起的 `CREATE TABLE` 仍会提交（容器 `northstar-qa-final-r7-fault-ddl-20261104` 保留该现场：两条 DDL 已提交、history 缺失）。该现场本身也满足"重启不得误判成功"（重跑同样被 1061 阻断），留作操作风险记录。
4. R7 源容器在执行期间退出（137），其 3385 端口被后续套件容器复用；所有脚本均有 `@@server_uuid` 身份守卫，无误写。M07/M03.a 已在此前完成，证据有效。

### 剩余 NOT VERIFIED

- 实体麦克风/设备验收（不在浏览器 MediaRecorder 覆盖范围，同历史口径）。

**PHASE 10D READY — GO TO 10E**（实体麦克风与上述 P2 观察随 10E 计划处理）
