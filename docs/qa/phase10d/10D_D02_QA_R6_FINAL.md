# Phase 10D-2 QA-EXEC R6 最终独立验收

日期：2026-11-04（Asia/Shanghai）。**PHASE 10D NOT READY — NO-GO TO 10E**。本轮未发现新的 P0/P1 产品缺陷；M03–M08 的完整故障恢复及部分旧功能回归仍缺正式证据。

## 候选和环境

- Git HEAD `8adac6d233d178010ba10660874098df802d5ea4`，分支 `codex/d02-core-r5-fix`。R5 原 219 项清单 SHA-256 `31a9a13065af5113a56929a2ba1aa5856f32228124b34750079fef7087683eb7`；逐项对照仅 `10D_FINAL_ACCEPTANCE.md` 因后续复测状态更新而不同，业务、迁移及测试源码相同。不能把原清单称为全量不变。
- R6 执行前冻结 240 项输入，清单 SHA-256 `54216a60bb44b1d2f315b70cd7b155bf3ca8f68d8d0b47cd82f4b3716c21faa8`。收尾补入 4 个构建/备份配置文件，它们与执行前源码副本逐字节一致；244 项完整清单 SHA-256 `1321596728510af57ff09b9a72b88fd78326597c9dc97f41741df12364e6ab95`。原命令日志仍绑定 240 项初始清单。见 `qa/phase10d-final-r6/evidence/candidate-identity-final.json` 与两份 manifest。
- 实际 JAR SHA-256 `771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6`，重建 class/resource 对照一致；浏览器 Web BUILD_ID `oeTUs8w5kWCV4O22yCFZm`。Node `22.23.2`、Java `21.0.12.1`、MySQL `8.4.9`，Flyway `012.11`；V012 checksum 与 49 个迁移 SHA 见 `r6-migration-inputs.json`、`*-flyway-history.log`。
- B08/B09/恢复源库：容器 `d70d64bb54801f6ef31edfd225340f0ce3097d8952d5fbee689ed5e2c49896fe`，`127.0.0.1:3383`，UUID `085adf79-d796-11f1-aedc-1a5123ebe7f1`，卷 `northstar-qa-final-r6-20261103-data`。浏览器库：容器 `3c5f99a330c3e7b7c1b6398db7401bb659af19866fb89e506561c48f7f2925ed`，`127.0.0.1:3384`，UUID `bf0b3967-d797-11f1-b54e-7a6234b27e10`，独立同名卷。初始 schema 均为 `northstar_phase01_test`，恢复 schema `northstar_restore_20261103145918` 位于 3383 容器。账号和媒体目录见两份 `database-identity.json`。

## B08：PASS

原创课程 A/B 的不同 LessonVersion、相同确认义项、各一次真实错误 Attempt 建立一张卡与两条来源。QA 以 `threading.Barrier` 同步真实 HTTP 请求，保存纳秒级重叠区间。B08-01 新来源与自评均 200；B08-02 两 eventId 同 rowVersion 为 200/409；B08-03 同 eventId 同 payload 并发返回同一 Attempt；B08-04 同 eventId 异 payload 为 200/409；B08-05 来源追加 200、旧版本自评 409；B08-06 自评后新增来源 200；B08-08 隔离库临时 `command_receipt` 触发器在提交前注入故障，首次 500 且 Attempt/回执为 0，移除后原 eventId 重试 200。B08-07 另用本地代理收到上游 200 后关闭客户端连接，客户端确实得到 `RemoteDisconnected`，原 eventId 重试 200、同一回执、结果仅一条。

B08 基线后是 **8 个不同的真实错误 Attempt 对应 8 条来源**、一张卡、3 条自评、rowVersion 4。第一次 QA 断言误算为 7 而退出 1；保留现场并用 HTTP Attempt ID 集合与 SQL 来源集合只读复核。B09 和响应丢失补验后，终态仍为 8 条唯一来源、5 条概念结果、rowVersion 6、reps 5，缺失回执 0，客观 Attempt 仍为 8。证据：`evidence/r6-b08-http.json`、`r6-b08-{baseline,after}-snapshot.json`、`r6-b08-result.json`、`r6-b08-07-response-loss.json`、`r6-final-db-audit.json`。

## B09：PASS

同一隔离库有 8 条跨课来源、至少 3 次概念自评及旧句卡 `cr-kp-3-reading` 的真实自评。正常停止/重启专属 API 后，对概念卡/来源/结果、回执、AttemptKnowledge、旧 review_item/source/result 八表逐行比较；旧概念和句卡 eventId 重放没有改变任何行。再提交合法新概念自评并第二次重启，八表逐行一致、rowVersion 合法推进、旧句卡原行不变。证据：`evidence/r6-b09-*-snapshot.json`、`r6-b09-result.json`。

## M03–M08：NOT VERIFIED

已执行的子实验：使用原版 `scripts/data-transfer.py` 和 QA 身份适配器对非空 3383 测试库备份，在新 schema 恢复；知识、Attempt、概念复习、旧句卡共 10 张关键表行数一致，`knowledge_occurrence.location_guard` 有实际数据且恢复后逐值一致，未出现 MySQL 3105。恢复目标启动真实 API，读取课程/概念/旧来源，新增错误 Attempt、概念来源和自评，原 eventId 重放、重启后八表逐行一致。恢复库跨概念与跨版本复合 FK 返回 1452，只追加触发器返回 1644，负例前后关键表哈希相同。截断备份被拒且未创建目标；新故障探针 schema 中通用 DDL 部分成功、DML 回滚均返回 1054，源库数据未变。证据：`evidence/r6-restore-result.json`、`r6-recovered-study-result.json`、`r6-negative-sql-{result,corrected}.json`、`r6-fault-probe-result.json`。

正式门槛仍缺：仓库 QA 计划 `10D_QA_TEST_PLAN.md` 只定义 D01-M03/M04/M05，找不到 M06–M08 原定义。本轮按用户“批准”继续了明确场景，未自行改写编号。M03 尚无实际 V012/Flyway 的 DDL 半成功、DML 中断、**history 登记失败**完整矩阵；通用 SQL 探针不能代替。恢复目标虽为独立 schema，却与源共享容器、卷和端口；没有独立卷恢复。备份中个人录音 0，原创测试 MP3 有 SHA，但不能证明非空录音媒体恢复；恢复过程中断后的真实恢复路径也未完成。因此 M03–M08 整体不得 PASS。

## Node、Playwright 和既有功能

- 本轮 Node `npm test`、`typecheck`、`lint`、`build` 均 exit 0，测试 **43/43**；Java 核心五套集成测试 **11/11**、package exit 0，含 D01 知识来源、D02 概念复习和 10C-2 测验规模/报告。日志及退出码在 `evidence/commands.jsonl` 和 `browser/evidence/commands.jsonl`。
- 新 3384 库、真实 8200 API/3207 Web 的 Playwright：0/1/20/21/22/100/101 卡，全部/到期、刷新、切换、重开、迟到请求、503 重试、重复加载、页外卡来源和自评均 PASS。101 卡时 82 受限来源、1 可见来源完整可达，字段白名单通过；API limit 1/20/100 遍历无重漏，limit 101 为 422。双标签同版本自评为 200/409，失败页面有明确冲突；断网 pending、联网原事件重试、刷新和 DB 每卡一结果/版本只推进一次通过。证据：`browser/evidence/matrix-*.json`、`pagination-api-results.json`、`dual-tab-{result,db-audit}.json`、`output/playwright/phase10d-final-r6/*.png`。
- R5 队列分页 P1 在 R6 独立环境定向 PASS。D01 Unicode/同形异义、撤回权限和来源链仅有核心测试与浏览器子集；旧 Demo 测验历史、10C-1 实际播放/恢复及 D01 全量没有本轮独立补齐，不能称 D01 全量 PASS。实体麦克风与 240 次声学测量未执行。

## 失败记录和门禁

本轮 QA 工具曾误算来源数、把合法新增句卡误判为旧卡变化、误读 SQL 日志首行、让跨版本负例先撞重复主键，以及浏览器构建后漏写清单身份。首次证据包验证脚本还将 SHA 与文件名的映射方向写反，失败包保留为 `northstar-phase10d-r6-final-sanitized-evidence.failed-verify.zip`；修正后重新独立校验。原 SQL 负例和首次浏览器构建命令保留。内部 SQL、Node、Java、浏览器命令使用唯一 runId 日志。**部分早期 Python 顶层失败仅有会话终端输出，缺完整原始文件日志**，不能声称满足本轮全部日志纪律。

未操作个人 3308/3100/8085，未触碰旧 3348/3349 失败现场；R6 库、卷、私有备份与故障 schema 保留，本轮 API/Web 已停止。已检查的隔离库历史没有污染；个人库未读取，无法作逐行结论。本轮未发现已确认未解决的 P0/P1，但缺验范围不能排除。

| 最终问题 | 结论 |
| --- | --- |
| R5 P1 独立环境通过 | PASS |
| B08 / B09 | PASS / PASS |
| M03–M08 | NOT VERIFIED；子实验见上 |
| Node / Playwright | PASS / PASS（所列矩阵） |
| D01 | 关键子集 PASS；全量 NOT VERIFIED |
| D02 整体 | NOT VERIFIED，受恢复和全量回归门禁限制 |
| 历史数据污染 | 已查隔离库无；个人库未接触 |
| Phase 10D 关闭、进入 10E | 否 / 否 |

下一步需取得 M06–M08 原定义，在新隔离目标补齐 V012/Flyway history 故障、独立卷和非空媒体恢复、D01/Demo/10C-1 回归及完整原始失败日志。此建议不授权部署、提交或开始 10E。

**PHASE 10D NOT READY — NO-GO TO 10E**
