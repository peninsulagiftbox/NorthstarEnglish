# Phase 10D-QA R7 P0/P1 修复与门禁收口记录

日期：2026-11-05（Asia/Shanghai）。范围：只修复 R7 确认的 P0/P1；不推进 10E。

## 修改内容

1. **P0：`COMPLETE` 缺失或篡改不再可恢复。** `scripts/data-transfer.py` 新增 `verify_complete`；restore 会在加载 JSON 后、任何 API 预检或目标创建前检查备份目录中的 `COMPLETE` 文件，并要求其内容等于 `learning.json` 的 SHA-256。
2. **P1：`review_result` 不再可 UPDATE。** 新增 `apps/api/src/main/resources/db/migration/V012_12__review_result_immutable.sql`，创建 `review_result_no_update` BEFORE UPDATE 触发器。未添加 DELETE 触发器，保持既有测试清理路径可用。
3. `data-transfer.py` 支持版本 012.12 快照；新增修复验收脚本 `qa/phase10d-final-r7/run_p0p1_fix.py`。

## 验证

- `python3 -I scripts/tests/test_data_transfer.py`：PASS，覆盖 `COMPLETE` 缺失、内容不匹配和匹配三种情况。
- 全新隔离 MySQL 容器 UUID `fdbae911-d868-11f1-ac49-22f976e3a644`。
- `QuizReviewIntegrationTest`：2/2 PASS；原 P1 断言现在按预期收到 `DataAccessException`。
- 迁移确认到 `012.12 success=1`；触发器确认为 `review_result_no_update / UPDATE`。
- 证据：`qa/phase10d-final-r7-fix/evidence/p0p1-fix-identity.json`、`p0p1-fix-result.json`、`p0p1-quiz-review.log`、`p0p1-history.log`、`p0p1-review-result-triggers.log`、`p0p1-data-transfer.log`。

## 边界与风险

- 首次隔离测试因沙箱阻止 localhost 连接失败，原始日志保留；提权重跑通过。该失败不是代码缺陷。
- 只添加 UPDATE 保护，不覆盖数据库端 DELETE；如产品契约要求完全 append-only，需另行评估 DELETE 保护对测试清理的影响。
- Phase 10D 仍为 **NO-GO TO 10E**；M03.a、M07 剩余中断场景、D01 全量、旧 Demo 完整闭环和 10C-2 全量仍未重跑。

## 2026-11-05 续：剩余门禁收口（用户指令"继续检查并自动修复，直至能进行下一阶段"）

### 新增 QA 执行件（只加测试基建，未改 CORE/迁移/业务代码）

| 文件 | 用途 |
| --- | --- |
| `qa/phase10d-final-r7/fault_ddl.py` | D01-M03.a 注入/重试/API 诊断/恢复；子进程 transfer 适配器 `phase10d_isolated.py` + `run_transfer.py` |
| `qa/phase10d-final-r7/backup_faults2.py` | M07 备份/恢复/媒体复制中断三类场景（子进程真实运行 data-transfer.py 并注入 SIGKILL） |
| `qa/phase10d-final-r7/demo_loop.py` | M08 旧 Demo 完整闭环：3397 恢复目标 + 固定 Playwright CLI 跑未修改的 `scripts/full-learning-loop.js` |
| `qa/phase10d-final-r7/run_suite.py` | 扩展 full/full2…full6 分组全量回归；对回归容器应用"学习者最小授权 + 知识注册维护授权"矩阵 |

### 运行与结果

1. **D01-M03.a PASS**：fault-ddl2 容器（3395）注入点为 V012.02 两条 DDL 之间——检测到 Flyway 会话阻塞在 `CREATE TABLE knowledge_occurrence` 的元数据锁等待后，先服务端 `KILL` 再 JVM `SIGKILL`；语句 1 已提交、语句 2 未提交、history 无 012.02、旧行逐值不变。重跑被 MySQL 1061 阻断且 history 登记 `012.02 success=0`。API 对故障目标启动失败（退出码 1、无 /health、日志含 1061）。故障前基线备份（SHA-256 记录在案）导入 3398 新容器后迁移至 012.11，API 读取 + 听写 attempt + 同 eventId 重放一致。证据：`qa/phase10d-final-r7/evidence/fault_ddl2/`。
2. **M07 8/8 PASS**：备份目录创建即 SIGKILL（无 COMPLETE、restore 拒绝且未建目标、重试 PASS）；恢复仅 1 表时 SIGKILL（关键行缺失、无媒体目录、重试逐表一致）；媒体复制阶段 SIGKILL（无 PASS、重试媒体齐全）；API 失败可诊断性同 M03.a。证据：`qa/phase10d-final-r7/evidence/r7-m07-interruption-result.json`，源库前后逐值一致。
3. **M08 PASS**：ROOT 全部 47 项测试分两组通过（`suite_full5` 46 项 + `suite_full6` 1 项，均 BUILD SUCCESS）；旧 Demo 完整学习闭环 7 项检查在 3397 恢复目标通过（`r7-demo-loop-result.json`）。

### 过程发现（P2，不阻塞）

1. 恢复授权矩阵缺知识注册写权限（`knowledge_concept` 等 7 表），恢复副本上知识注册会被拒——待产品决策是否扩展 `data-transfer.py` 恢复授权。
2. `MultiCourseIntegrationTest` 无 cleanup 且与 `KnowledgeSourcesIntegrationTest` 复用 `fixture-a/b`，共享容器全量必然冲突；本轮分两组隔离收口，属测试基建问题。
3. JDBC `socketTimeout=3000` 不中止服务端被 MDL 阻塞的 DDL（首轮注入现场 fault-ddl 容器保留：两条 DDL 已提交、history 缺失、重跑被 1061 阻断）。
4. R7 源容器执行期间退出（137），3385 端口被后续套件容器复用；所有脚本有 `@@server_uuid` 守卫，无误写。

### 状态

Phase 10D **GO TO 10E**（详见 `docs/qa/phase10d/10D_R7_FINAL_ACCEPTANCE.md`）。实体麦克风验收仍未覆盖（历史口径）。本轮全部在隔离容器执行；未部署、未操作个人 3308/3100/8085、未删除任何故障现场。

## 2026-11-05 续：P2 恢复授权扩展落实（用户批准"全部同意"）

按用户批准扩展 `scripts/data-transfer.py` 恢复授权矩阵：恢复副本的 `northstar_app` 新增
`knowledge_concept`、`knowledge_concept_revision`、`knowledge_occurrence`、`exercise_sentence`、
`exercise_knowledge`、`legacy_knowledge_link` 的 INSERT，以及 `knowledge_projection` 的 INSERT,UPDATE。

验证（3398 隔离容器，临时库 `northstar_grant_verify_tmp` + 临时账号，验证后已删除）：

1. `python3 -I -m unittest discover -s scripts/tests -p 'test_data_transfer.py'`：3/3 PASS（含 COMPLETE 标记校验）。
2. 由脚本提取的 36 条 GRANT 应用后 `SHOW GRANTS`：新增 7 表权限逐条在列，整库仍仅 SELECT。证据：`qa/phase10d-final-r7-fix/evidence/p2-grant-verify/`（grants.sql、show-grants-after.sql、negative-verify.txt、cleanup.txt）。
3. 负向：仅 INSERT 的 `knowledge_concept` 执行 UPDATE 被拒（ERROR 1142）；正向：`knowledge_projection` 空表 UPDATE 放行（ROW_COUNT()=0）。
