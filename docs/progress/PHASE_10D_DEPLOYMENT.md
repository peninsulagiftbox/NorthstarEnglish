# Phase 10D-1 完成、独立复验与本地部署报告

日期：2026-11-01（Asia/Shanghai）。结论：**D01 复验 PASS；已推送 GitHub 并部署个人环境 012.07**。本报告为自包含摘要，供独立复核（ChatGPT）使用；全部原始证据路径在文中列出，均绑定同一最终候选。

## 1. 范围与绑定候选

| 项 | 值 |
| --- | --- |
| 推送 HEAD | `02afc4800e046a97e8ed7d81a6665e372193364b`（`origin/main`，7 个提交 `ff0dbe1..02afc48`） |
| 部署运行时 | JAR SHA-256 `14169f2ddab03525af166a72f9feb2b4ec7bf8eea7825657289223ea51d57ef6`；Web BUILD_ID `KksYjZGlUjYg0pKaGsvll` |
| 数据库版本 | 个人库 `northstar_english`（127.0.0.1:3308）011.09 → 012.07，46 条迁移全部 success=1 |
| 独立复验 | `docs/qa/phase10d/10D_QA_D01_RETEST.md`（PASS，附前置条件及其关闭记录） |

本轮内容：10D-1 知识概念登记/出现位置/冻结证据/浏览（含 V012_01–V012_07 迁移）、独立 QA 复验七项缺陷修复（QA-BUG-001…007 + R-QA-008）、QA 前置条件（测试夹具适配）落入候选、受控本地部署。D02 未实现、未开始。

## 2. 提交清单

| 提交 | 内容 |
| --- | --- |
| `9de8147` | 后端 knowledge 包、V012_01–07 迁移、知识/测验集成测试、OpenAPI（29 文件，+1701/-22） |
| `38ef2e7` | 10D 隔离 runner、10C 回归脚本（8 文件） |
| `8a3dcc2` | 10D-1 实施报告、QA 复验报告、QA 工具（24 文件） |
| `b7502cc`/`183413a`/`02afc48` | 受控部署脚本及两处修正 |
| `a0c360d` | 部署证据目录保持本地（.gitignore） |

原始运行证据、构建产物、备份、凭据按惯例不入库（`/docs/handoff/evidence/phase10d*/**` 已 ignore）。

## 3. 七项缺陷复验结果（全部实测，非静态）

证据均来自 3340 隔离容器（`northstar-phase10c2-20261031d-empty`，server_uuid `7ca8f0fc-d50a-11f1-b8e2-92808e97a3e8`）与 QA worktree；逐项方式、错误码与日志见 `docs/qa/phase10d/10D_QA_D01_RETEST.md` §2。

| 缺陷 | 数据库/运行证据 |
| --- | --- |
| QA-BUG-001 lesson 级重复 occurrence | 第二条直插被 `1062 uq_occurrence_location`（location_guard 哨兵 `L`）拒绝 |
| QA-BUG-002 Unicode 空白 | `KnowledgeConceptsTest` 4/4 + 规范化集成 1/1（NBSP/U+2007/U+202F/NFC/撇号/255–256 码点） |
| QA-BUG-003 attempt 快照不可变 | UPDATE/DELETE 均 `45000`；runtime 账号另有 `1142` 权限拒绝（双保险） |
| QA-BUG-004 修订不可变 | UPDATE/DELETE 均 `45000 Knowledge concept revisions are append-only`；relations_sha256 已含修订内容 |
| QA-BUG-005 撤回课聚合泄露 | 集成测试 browse 段 + invariant I-08：撤回后 lessonCount 下降、受限行仅元数据 |
| QA-BUG-006 多 confirmed 修订 | 旧修订 occurrence 保留在列表/详情，历史 attempt 快照逐字节不变 |
| QA-BUG-007/R-QA-008 范围校验 | paragraph 级 occurrence 对全部来源句同段校验；N-04/N-05 被 `3819 ck_occurrence_scope` 拒绝 |

## 4. 验证矩阵（原始退出码均为 0，日志在 `docs/handoff/evidence/phase10d/`）

| 检查 | 证据 |
| --- | --- |
| `KnowledgeSourcesIntegrationTest`（真实 MySQL，夹具修复后复跑） | `knowledge-sources-final-1793508550777035000.log`（首跑失败原件 `…8745000.log` 保留） |
| `KnowledgeNormalizationIntegrationTest` + `KnowledgeConceptsTest`（5/5） | `knowledge-normalization-1793468868902371000.log` |
| `negative_cases.sql`（N-01..N-15 适用项全拒） | `knowledge-sql-negatives-1793469929467550000.log` |
| `invariant_checks.sql` 对账（孤儿 0、I-07/I-08 一致） | `knowledge-invariant-checks-1793469941039597000.log` |
| 触发器守卫探针（N-07/attempt/修订直写） | `qa7-immutable-probe*` 5 份日志 |
| 运行账号 `SHOW GRANTS`（无 ALTER/DROP/TRIGGER/DDL） | `grants-audit-1793469941435247000.log`（R-QA-009 关闭） |
| 迁移故障演练 7/7（V012_01–07 中断/回滚/history 异常） | `migrations/fault-*-acceptance.json` |
| 10C-2-R1 回归（参数化报告 + verifiedRun） | `quiz-report-r1-…`、`quiz-scale-…` |
| Web typecheck/lint/test/build、Python 单测 18/18 | `web-*-17934702*.log`、`py-unit-tests-…` |
| HTTP 只读核心（health/404/列表/恢复副本） | `http-*`、`restored-*-final` |
| 备份→恢复→二次启动（`data-transfer --phase10d`，行数+媒体哈希） | `restored-health-final-…`、`qa/phase10d/evidence/final-target-identity.json` |

命令、argv、cwd、HEAD、原始退出码与日志哈希逐条在 `docs/handoff/evidence/phase10d/execution-commands.jsonl`。

## 5. 部署过程与结果

脚本：`scripts/deploy-phase10d.py`（RUN `20261101T125536`，复用 10C 受控框架：源身份核验→新鲜备份→隔离演练→个人迁移→新运行时→两次启动验证）。

1. 新鲜备份：逐行快照 + mysqldump + 内容/录音副本，`result.json` PASS。备份目录 `.local/phase10d-release/20261101T125536/backup/`（私有，不入库）。
2. 隔离演练：备份恢复→011.09→012.07→启动→重启，旧表逐格比对一致（`oldCellsExact/twoRestartsExact=true`）。
3. 个人库执行相同迁移并授权：`northstar_app` 新增 `attempt_knowledge` INSERT；TRIGGER 权限仅 `northstar_migrator`。4 个不可变触发器已在个人库确认存在。
4. 旧 JAR/Web 构建保留为 `previous-api.jar`、`previous-web-build/`；未删除任何容器/卷，未执行 repair，未修改 history。
5. 推送后服务进程曾停止，已用 `dev-up.sh` 受控重启；当前 API/Web health UP（012.07），`/knowledge/concepts` 200，启动自检全部 PASS（历史证据只读）。

部署记录：`docs/handoff/evidence/phase10d-deployment/20261101T125536/{release.json,result.json,commands.jsonl}`。

## 6. 回滚边界

不直接把旧 JAR 连到 012.07 库。若需回退：先在全新隔离库用上述备份恢复并核验，个人库覆盖需单独授权。本轮未回写备份。

## 7. 未解决项与未测范围（复核重点）

1. **R-QA-010：BLOCKED_BY_CORE**——概念复习 sources 接口属 D02，未实现；D01 通过不关闭此项。
2. **D02 全部 NOT VERIFIED**——概念复习卡/CAS/幂等/自评分离、恢复续学端到端、10D 整体验收均未开始；**10D 不得整体宣布通过，10E 无进入条件**。
3. **浏览器 UI 未覆盖**：两课并列概念浏览、版本切换与撤回受限提示的 UI 呈现（API 层已验证）；本阶段无录音路径改动，实体麦克风/Safari 沿袭 10B/10C 结论未重测。
4. QA 首跑失败原件证明候选提交前夹具为红（已修复并复跑绿色）；复核时可直接比对两份 `knowledge-sources` 日志。
5. 个人库 012.07 升级包含运行账号新授权；生产收紧场景（非本地单机）未评估。

## 8. 建议复核入口

1. `docs/qa/phase10d/10D_QA_D01_RETEST.md`（缺陷逐项 + 证据路径）。
2. `docs/handoff/evidence/phase10d/execution-commands.jsonl`（命令与退出码流水）。
3. `docs/handoff/evidence/phase10d-deployment/20261101T125536/result.json`（部署 PASS 断言）。
4. 脱敏证据包：`output/review/phase10d-d01-retest-sanitized-evidence.zip`（SHA-256 `e9f6fb4c79ca3f1676ac179de154d4fcb2ccc9c1d4d337600b6330de79f35281`，43 文件）。
