# Phase 10D-QA R7 Flyway 故障恢复验收

日期：2026-11-04（Asia/Shanghai）。结论：**D01-M03.b 与 D01-M03.c PASS；D01-M03.a NOT VERIFIED。**

## 身份与候选

- 唯一 runId：`qa-r7-6603e1b1053b4f5fa5b66263c4b97149`。
- 初始冻结候选：399 项，SHA-256 `e64d76758b50dfa4f235d5c631e5bbba7e93bde00351beccb82e88124c615e6d`。
- JAR SHA-256：`771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6`。
- Java 21.0.12.1，Node 22.23.2，MySQL 8.4.9，Flyway 012.11。
- 源容器 3385 UUID `35965c3f-d823-11f1-be71-b6b8e525f6a4`；故障与恢复目标均为独立容器/卷。

## D01-M03.c：V012.10 history 登记失败

1. 3387 目标初始化到 012.09 后，通过回收 `northstar_migrator` 对 schema 的 INSERT 权限阻断 history 写入，再启动真实 Spring Boot/Flyway 到 012.11。
2. 结果：`attempt_knowledge` 唯一索引与 `concept_review_source` 表存在，说明 DDL 已提交；`flyway_schema_history` 无 012.10，说明登记失败。
3. 首次执行退出码 1；同目标重试退出码 1，未自动修补 history，也未盲目继续迁移。
4. `lesson`、`lesson_version`、`sentence`、`exercise_attempt`、`personal_recording` 前后哈希一致。
5. 故障前备份在 3388 新卷恢复，UUID `f3749106-d824-11f1-9c2f-5e9e4cc1312d`，正常迁移到 012.11 并通过课程读取。

证据：`qa/phase10d-final-r7/evidence/fault_history/result.json`、`flyway-history-register-failure.log`、`flyway-unsafe-retry-blocked.log`、`before-hashes.json`。

## D01-M03.b：V011.06 事务内 DML 回填失败

1. 3389 首套夹具已有 `exercise_set` 行，V011.06 在第一处 INSERT 因 MySQL 1062 失败，未到达受控第二处 INSERT。`result-correction.json` 明确该套不计 PASS。
2. 3390 第二套清理新增格式集合后，保留第一处 INSERT 权限、拒绝 `exercise_set_item` INSERT，真实 Flyway 到达第二处回填写入。
3. MySQL 1142 命中 `exercise_set_item`，执行退出码 1；已写入的前一事务数据回滚，四个对账表前后哈希一致。
4. history 尾部为 `011.06 success=0`。故障前备份在 3391 新卷恢复，UUID `52e9255e-d854-11f1-ad11-8aed37123972`，迁移到 012.11。

证据：`qa/phase10d-final-r7/evidence/fault_dml2/result.json`、`flyway-dml-backfill-failure.log`、`before-hashes.json`；首套失败保留在 `qa/phase10d-final-r7/evidence/fault_dml/`。

## 未通过与边界

- D01-M03.a 未构造多语句 DDL 进程终止用例，保持 **NOT VERIFIED**；因此 D01-M03 整体不能记全量 PASS。
- 未使用手工失败 SQL 冒充 Flyway，未修改迁移 checksum，未执行 Flyway repair，未伪造 history。
- 原失败目标、首次失败日志和 3389 无效前置条件证据全部保留。
