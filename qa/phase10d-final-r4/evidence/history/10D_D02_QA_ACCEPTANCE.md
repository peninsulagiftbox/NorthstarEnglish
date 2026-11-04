> 2026-11-02 最新独立复测：P1受限分页500及合法游标422已关闭，本次定向PASS，阶段整体CONDITIONAL PASS。新JAR771a72e8…，冻结336项输入；独立3374库7/7集成回归、原3364库只读59表哈希及真实Playwright通过。详见 [最新复测报告](10D_D02_QA_P1_RETEST.md) 与 [最终验收状态](10D_D02_QA_FINAL_ACCEPTANCE.md)。以下保留历史记录，不以旧候选结果替代新候选未测项。

# Phase 10D-D02 QA 验收结论

日期：2026-11-01（Asia/Shanghai）。QA-EXEC 第一轮（FAIL）与第二轮（CORE R1 冻结候选复测）均已完成。

## 结论：**CONDITIONAL PASS**

依据（第二轮全部在 QA 独立隔离库实测，候选 27 文件+JAR 哈希独立复验一致）：

1. 五项缺陷全部修复并复验：建卡 INSERT 显式传协议值且并发收敛于单卡（001）；约束错误 → 500 `DATA_CONFLICT` 非重试、暂态才 503（002）；夹具顺序、cleanup（含 study_stage）与 replay 语义（003/004/005）——`ConceptReviewIntegrationTest` 在 QA 独立环境全量 PASS。
2. 回归：D01 `KnowledgeSourcesIntegrationTest`（含 V012_08 完整性负例）PASS；`QuizScale`+`QuizReportR1` 5/5 PASS；Python 18/18 OK。
3. 第一轮提出的阻断项（来源泄露/跨概念/CAS 丢更新/错误成绩/旧记录改变）均未发现；对应矩阵已在真实 MySQL 上执行并通过。

## 附加条件（最终签收前必须补齐）

1. 备份/恢复演练（F 组 M03–M08：生成列恢复、新表完整恢复、故障恢复、跨 Concept 复合 FK 破坏性负例、恢复后续学）。
2. 重启持久性（B09：容器/应用重启后 due/reps/row_version/result 逐值不漂移）与来源追加×自评并发竞争（B08）。
3. Playwright 浏览器流程（多源卡、双 Tab CAS、断网丢回执、撤回受限展示）与 Node 四项在 QA 侧独立复跑（当前为 CORE 自证 + 候选字节一致）。

## 验收门槛（维持）

来源泄露（D 组）、跨概念关联（A05/A06/M06）、CAS 丢更新（B01/B04）、错误成绩生成（C05/C06）、旧学习记录改变（E 组）任一未通过即改判 FAIL。

## 解除条件

附加条件三项补齐并复核通过后可改判 PASS。不自动开始 10E；不操作个人 3308/3100/8085；不擅自提交、合并、部署。

边界：不自动开始 10E；不对个人 3308 数据库或个人服务做任何操作；不擅自提交、合并或部署。
