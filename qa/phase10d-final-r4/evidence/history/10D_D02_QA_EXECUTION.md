> 2026-11-02 最新独立复测：P1受限分页500及合法游标422已关闭，本次定向PASS，阶段整体CONDITIONAL PASS。新JAR771a72e8…，冻结336项输入；独立3374库7/7集成回归、原3364库只读59表哈希及真实Playwright通过。详见 [最新复测报告](10D_D02_QA_P1_RETEST.md) 与 [最终验收状态](10D_D02_QA_FINAL_ACCEPTANCE.md)。以下保留历史记录，不以旧候选结果替代新候选未测项。

# Phase 10D-D02 QA 执行记录

日期：2026-11-01（Asia/Shanghai）。角色：独立 QA。

## 1. 本轮实际执行（QA-PREP）

| 命令 | cwd | 退出码 | 结果 |
| --- | --- | --- | --- |
| `git status --short --branch && git log --oneline -5` | 主 checkout | 0 | 确认主树存在未提交 D01 整改（只读参考，未触碰） |
| 文档读取与 `rg` 定向检索（10D 计划、D01 门禁、目标数据模型、验收计划、10C-2、V004/V007、QuizReviewController、SimpleScheduler、KnowledgeSources） | 主 checkout / QA worktree | 0 | 现状核对完成（测试计划 §1.2） |
| `create_worktree`（managed，ref=`a5084cb`） | — | 成功 | QA worktree `worktree-10d-d02-qa` 建立并写入本目录文档 |
| `python3 -m json.tool` × 4（D02 fixture 文件） | worktree | 0 | 4 份原创合成 fixture JSON 语法有效 |
| `sh qa/phase10d2/tools/check_candidate_readiness.sh` | worktree | 1 | QA-PREP 时点 NOT READY（后续 CORE 落地 D02 候选） |

## 1.1 QA-EXEC 第一轮（2026-11-01，CORE 工作树候选快照）

环境：QA 专用容器 `northstar-qa-d02-20261101`（MySQL 8.4.9，127.0.0.1:3348，独立卷，server_uuid `c9899036-d5d2-11f1-a04e-4a84c4080faa`），schema `northstar_phase01_test`（项目身份播种后由应用 Flyway 迁移至 012.11），JDK21=`/Users/wangshiqi/Project/NorthstarEnglish/.local/jdk21/jdk-21.0.12.1+1`，测试音频 `original-test-tone.mp3`（sha `abba3072…`）。个人 3308/3100/8085 未连接。候选快照：主工作树 a5084cb+未提交改动，逐文件核验与 QA 基线一致（`evidence/qa-candidate-baseline-sha256.txt`）；CORE 冻结清单未含 D02 文件（清单漂移已在缺陷报告提示）。

| 运行 | 退出码 | 结果 |
| --- | --- | --- |
| run1–run3（`mvnw test -Dtest=ConceptReviewIntegrationTest`） | 1 | 环境引导问题（密码格式、身份播种、内容初始化），未到被测代码 |
| run4 | 1 | **QA-D02-BUG-003**：登记先于建题，422 `KNOWLEDGE_CONTEXT_MISMATCH` |
| run5/run6 | 1 | 403 LOCAL_ACCESS_ONLY（需 WEB_PORT=3196）→ 修复后 **QA-D02-BUG-001/002**：建卡 INSERT 1364 → 503 |
| run7 | 1 | 诊断种子尝试（FK 1452，概念未登记，预置不可行） |
| run8（诊断构建 v1：INSERT 补两列 + 夹具顺序） | 1 | 主体推进到 replayAndAppend 后被 **BUG-004** cleanup FK 1452 掩盖 |
| run10（+replay 相同 body 修复） | 1 | 编译错误（QA 补丁笔误），已修 |
| run12（诊断构建 v2） | 1 | 主体失败被 cleanup 异常掩盖；后续 run14 证实同因 |
| run13（清场后保留现场模式） | 1 | **BUG-005**：`a third real attempt appends a source expected 3 but was 4` |
| run14（保留现场复跑） | 1 | 同 BUG-005 稳定复现；现场 DB 状态存档 `run14-final-db-state.txt`（4 来源逐行回链真实 attempt/occurrence/concept；相同 body 重放返回同一 attemptId 且不重复入库） |

诊断构建差异存档：`evidence/ConceptReviewIntegrationTest.qa-diag.java.txt`；运行后候选文件字节已恢复并复验（`qa-candidate-baseline-sha256.txt`）。原始日志：`evidence/qa-d02-mvn-run6/8/12/14.log`、`init-content.log`。

## 1.2 QA-EXEC 第二轮（2026-11-01，CORE R1 冻结候选）

候选：CORE R1 冻结清单 27 文件（清单哈希 `087f849df28d66d1c80d48e5328322c3c385c152ea3ea65313e87b5f4703b787`），QA worktree 逐文件复制后以 CORE 自带 `verify-candidate.sh` 独立复验 PASS；JAR SHA-256 `cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb` 与 R1 报告一致。CORE 冻结清单已覆盖 D02 文件（含测试与运行说明 `run-instructions-20261101.md`），第一轮清单漂移问题已解决。

环境：全新容器 `northstar-qa-d02-r2-20261101`（MySQL 8.4.9，127.0.0.1:3349，独立卷，server_uuid `0266daed-d5e7-11f1-8e89-fa2ac2ebd15d`），schema 每套件重建，demo 内容合成初始化；个人 3308/3100/8085 未连接。

| 验证 | 退出码 | 结果 |
| --- | --- | --- |
| `ConceptReviewIntegrationTest` 全量（冻结候选，QA 独立环境） | 0 | **PASS**（Tests run: 1, Failures: 0, Errors: 0）：两课同概念多来源追加、相同 eventId+相同 payload 重放、异 payload 409、stale rowVersion 409、并发 CAS 单赢家、事务内约束失败 → 500 `DATA_CONFLICT` 非重试且零状态变化、自评不产生 attempt/run/分母变化、旧句卡保护、撤回受限来源字段裁剪与 visibleSourceCount 口径、分页游标 |
| 测试后 DB 对账 | 0 | 全表清理完成无残留（cleanup 修复生效）；`qa/phase10d2/evidence/qa-r2-reconciliation.txt` |
| `KnowledgeSourcesIntegrationTest`（D01+V012_08 回归） | 0 | PASS |
| `QuizScaleIntegrationTest` + `QuizReportR1IntegrationTest`（10C-2-R1 回归） | 0 | PASS（5/5） |
| `python3 -m unittest discover -s scripts/tests` | 0 | OK（18/18）；QA worktree 无 `.env` 生成 |
| Node typecheck/lint/test/build | — | 未独立复跑（CORE R1 报告全过 + 候选字节一致；web 无独立 node_modules，标记 CORE 自证） |

本轮**未运行**任何 Maven/MySQL/HTTP/Playwright 测试；未创建任何数据库、容器或 schema；未连接个人 3308/3100/8085。

## 2. QA-EXEC 执行清单（候选冻结并获授权后）

按 `10D_D02_QA_TEST_PLAN.md` §6 顺序执行。每条命令届时在此登记：时间、cwd、argv（脱敏）、原始退出码、日志位置与 SHA-256。

| 组 | 状态 |
| --- | --- |
| A 多来源聚合 | 部分（诊断构建下 A01/A04/A05 实证：三来源聚合、逐行回链、跨概念 FK 拒绝；A02 幂等重放实证；其余 NOT VERIFIED） |
| B CAS/幂等 | NOT VERIFIED（未执行到） |
| C 自评真实性 | NOT VERIFIED（未执行到） |
| D 权限 R-QA-010 | NOT VERIFIED（未执行到） |
| E 旧数据保护 | 部分（run14 现场：重复错误作答按既有规则更新旧句卡 row_version，自评段未执行到） |
| F 备份/迁移 | 部分（M02 结构实证：V012.09–11 应用、三表+append-only 触发器存在；M03–M08 NOT VERIFIED） |
| 浏览器 Playwright 流程 | NOT VERIFIED |

## 3. 隔离声明

QA worktree：`worktree-10d-d02-qa`（基线 `a5084cb`）。独立证据目录 `qa/phase10d2/`（执行阶段创建）。未修改 CORE 主工作树任何业务代码、迁移或 QA 既有文件；未提交、未合并、未部署。
