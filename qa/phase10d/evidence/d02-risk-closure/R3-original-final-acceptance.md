# Phase 10D-D02 QA 最终验收（R3 补验）

日期：2026-11-01（Asia/Shanghai）。执行角色：独立 QA-EXEC R3。
前置：R2 结论为 CONDITIONAL PASS（`10D_D02_QA_ACCEPTANCE.md`），三项附加条件为 B08/B09、F 组 M03–M08、Node+Playwright 独立复跑。

## 结论：**PASS**

R2 列出的全部附加条件已在冻结候选上独立补验并通过；未发现新的 P0/P1 缺陷。D02 升级为最终 PASS，可进入用户审核；不自动开始 10E。

## 1. 固定候选（R3 复验）

| 项 | 值 |
| --- | --- |
| 冻结清单 | 27 文件，清单哈希 `087f849df28d66d1c80d48e5328322c3c385c152ea3ea65313e87b5f4703b787` |
| 冻结校验 | 主 checkout 与 QA worktree 双侧 `verify-candidate.sh` 均 PASS（字节一致） |
| 候选 JAR | `cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb`（主 checkout `apps/api/target`；QA worktree 本地 JAR 为 R1 诊断构建 `8ef2ef6b…`，R3 全部使用主 checkout 冻结 JAR，未混用） |
| V012.01–11 | 11 个迁移 SQL SHA-256 与 R2 一致，见 `qa/phase10d/evidence/v012-migration-sha256-r3.txt` |
| 前端构建 | QA worktree `apps/web` 独立 `npm ci`（364 包，node 22.23.2）+ build，BUILD_ID `ufpzJFXUS7-9gLpbt0x5D` |

QA 执行代码与冻结候选一致性：B08/B09/M03–M08/Playwright 全部通过主 checkout 冻结 JAR + QA worktree 前端构建执行；无 QA 诊断副本混入。

## 2. 隔离环境（R3 现场）

| 实例 | 身份 |
| --- | --- |
| 源/续学库 | 容器 `northstar-qa-d02-r3-20261101`，MySQL 8.4.9，`127.0.0.1:3350`，server_uuid `6b1d2208-d5ea-11f1-afc1-aecb2137fbec`，schema `northstar_phase01_test` |
| 恢复目标库 | 容器 `northstar-qa-d02-r3-restore`，MySQL 8.4.9，`127.0.0.1:3351`，server_uuid `ac693853-d5ee-11f1-8540-3267e5db2ba0`，schema `northstar_restore_20261101202000` |
| 前后端 | API `127.0.0.1:8177` / Web `127.0.0.1:3197`（仅 QA 栈，浏览器验证窗口内运行并已停止） |
| 保留现场 | 第一轮 3348、第二轮 3349 容器原样保留；R3 两个容器与 `/private/tmp/qa-r3` 日志未清理 |
| 个人环境 | 未连接个人 3308 数据库与 3100/8085 服务（进程 14757/14758 为个人 service_runner，未触碰） |

## 3. B08 并发与 CAS（PASS）

真实 HTTP 并发（线程屏障同时提交来源追加 + CAS 自评 + 相同 eventId 重放 + 旧 rowVersion 提交）。11 项断言全部通过：来源全部保留、无重复来源、卡片唯一、CAS 仅一次合法推进（row_version 1→2、reps 0→1）、重放零新增、无孤儿结果、回执恰好 +2、客观测验不受影响。原始时间线：`qa/phase10d2/evidence/qa-r3/b08-timeline.txt`；驱动：`b08_concurrent.py`。

## 4. B09 重启持久性（PASS）

逐值快照（card/source/review_result/command_receipt/due_at/reps/row_version/旧 review_item）在 API 重启前后字节一致（SNAPSHOT_IDENTICAL=True），重启后幂等重放零新增。快照：`b09-before/after/after-replay.txt`；驱动：`b09_restart.py`。

## 5. F 组 M03–M08（全部 PASS）

| 组 | 结果 | 证据 |
| --- | --- | --- |
| M03/M04 STORED 生成列 + 全表逻辑备份恢复 | PASS | 57 张表逐 PK 逐值一致；3 个 STORED 生成列重算一致；26 触发器原文重建；109 FK 零孤儿；媒体 32 文件 SHA-256 一致（`m03-m04-run.log`） |
| M05 空库 + 旧备份升级路径 | PASS | `upgrade`（旧备份→010.06→012.11）与 `empty`（空库→012.11）双路径，各自双启动快照一致（`migrations/upgrade-acceptance.json`、`empty-acceptance.json`，均为冻结 JAR 重跑） |
| M06 DDL/DML 故障与恢复 | PASS | 7 个故障角色（fault-ddl/dml/history/04/05/06/07）全部在冻结 JAR 下重跑：已提交 DDL 识别、history 未变、旧数据逐值一致、失败目标保留 |
| M07 跨 Concept/Version 来源负例 | PASS | N1 bank 卡引用 riv 来源 → 1452（card-concept FK）；N2 同概念第二卡引用错误 version → 1452（五列复合 FK）；测试后库计数不变（`m07-run.log`） |
| M08 恢复目标真实续学 + 重启 | PASS | 恢复库上新错误 attempt 追加来源、新概念（cr-bank-riv）自动建卡（sources 3→5、cards 1→2）、幂等重放零新增、重启前后快照逐值一致（`m08-run.log`）。首次驱动因选项正误标注错误（river 用了正确答案）被纠正后重跑，属测试驱动缺陷而非业务缺陷 |

## 6. Node 四项（QA worktree 独立运行，全部 PASS）

| 检查 | 退出码 | 结果 |
| --- | --- | --- |
| typecheck | 0 | PASS |
| lint | 0 | PASS（1 个既有 unused-vars warning，非本轮引入） |
| test | 0 | 36/36 PASS（8 个测试文件） |
| build | 0 | PASS，BUILD_ID `ufpzJFXUS7-9gLpbt0x5D` |

日志：`qa/phase10d2/evidence/qa-r3/node-*.log`。

## 7. Playwright 浏览器流程（PASS）

MCP Chromium（无头 1440×900）在隔离 3197/8177 栈执行，账号 `local`，固定候选 JAR + 独立构建前端 + 隔离库：

| 项 | 结果 |
| --- | --- |
| 旧句卡 + 新概念卡同时展示 | PASS |
| 两课多个真实来源（cr-a×2 + cr-b×1） | PASS |
| 来源详情可回溯（attemptId/lesson/句子/时间戳） | PASS |
| 合法自评 + 刷新恢复（rv 2→3、reps 0→1、队列消失后计数一致） | PASS |
| CAS 冲突提示（旧 rowVersion → 409 中文提示） | PASS |
| 连续点击不重复提交（快速双击 results 仅 +1） | PASS |
| 撤回来源不泄露（无撤回端点 → 404，正文/音频/聚合未变） | PASS |
| 空队列 / 异常 / 网络错误状态 | PASS（空队列文案、404 复习卡不存在、断网"暂时无法连接本地服务…重新加载"） |

明细：`qa/phase10d2/evidence/qa-r3/playwright-summary.log`。浏览器验证产生的合法写入（1 次自评 + 1 次双击去重）均属验证行为，已在对账中单独列示。

## 8. 三轮缺陷与修复状态

| 缺陷 | 修复轮 | R3 状态 |
| --- | --- | --- |
| QA-D02-BUG-001 建卡 INSERT 缺 prompt_kind/protocol_version | CORE R1 | PASS（真实隔离库复测不再出现 1364/503；M08 恢复库自动建卡亦验证协议值写入） |
| QA-D02-BUG-002 约束错误误包装 503 可重试 | CORE R1 | PASS（R2 全量 `ConceptReviewIntegrationTest` 覆盖 500 `DATA_CONFLICT` 非重试；R3 无回归） |
| QA-D02-BUG-003 夹具登记顺序 | CORE R1 | PASS |
| QA-D02-BUG-004 cleanup FK 顺序 / 异常掩盖 | CORE R1 | PASS |
| QA-D02-BUG-005 replay 断言 expected 3 but was 4 | CORE R1 | PASS（R2 复核为第 4 条为同 eventId 新 attempt 的合法来源；R3 B08/M08 再次验证幂等与追加语义） |

## 9. D01 / 10C-2 关键回归（R2 已独立完成，R3 未回归改动）

`KnowledgeSourcesIntegrationTest` PASS（含 V012_08 完整性负例）；`QuizScaleIntegrationTest` + `QuizReportR1IntegrationTest` 5/5 PASS。R3 未修改任何业务文件（候选字节一致），回归结论继续有效。

## 10. 已知未验证项与残余风险

1. Playwright 的"撤回受限来源字段裁剪"通过 404 无撤回端点路径验证（当前候选未提供撤回 API）；受限字段裁剪逻辑本身由 R2 `ConceptReviewIntegrationTest` D 组断言覆盖，未做双浏览器并发撤销展示。
2. B08 的并发为双线程真实 HTTP 竞争，非多机压测；更高并发下的连接池行为未测。
3. M05/M06 复跑使用既有隔离容器（同名重建卷），旧备份与容器身份在 pre-r3-backup 保留；未新建独立命名容器。
4. 浏览器验证窗口内服务由脚本管理并已停止；如需复现需按 `run-browser-mcp.sh` + `serve-web-api.sh` 重新拉起（脚本存档在 /private/tmp/qa-r3，证据包含摘要）。
5. QA 独立复测本身完成后仍需用户确认签收。

## 11. 证据包

`output/review/northstar-phase10d2-r3-sanitized-evidence.zip`：B08/B09/M03–M08/Node/Playwright 日志与驱动、迁移哈希、验收 JSON 摘要、本报告副本。不含凭据、个人数据、录音或密钥；两轮历史现场（3348/3349）容器与日志保留未清理。
