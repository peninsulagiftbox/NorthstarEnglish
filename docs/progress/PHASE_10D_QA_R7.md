# Phase 10D-QA R7 阶段记录

日期：2026-11-04（Asia/Shanghai）。结论：**PHASE 10D NOT READY — NO-GO TO 10E。**

## 改动文件

- 新增 `docs/qa/phase10d/10D_R7_FLYWAY_FAULT_REPORT.md`、`10D_R7_INDEPENDENT_RESTORE.md`、`10D_R7_LEGACY_REGRESSION.md`、`10D_R7_FINAL_ACCEPTANCE.md`。
- 在 `docs/qa/phase10d/10D_R7_RECOVERY_MATRIX.md` 追加 R7 执行补充；原核定章节保留。
- 新增 `qa/phase10d-final-r7/backup_faults.py`、`independent_restore.py`、`recovered_study.py`、`run_suite.py`、`writing_seed.py` 等本轮 QA 工具；不改 CORE 与已执行迁移。
- 生成完整候选补充清单和 `output/review/northstar-phase10d-r7-final-sanitized-evidence.zip`。
- 完整候选清单 418 项；初始 399 项和 19 项补充均校验通过。
- 脱敏证据包 799 个文件，独立解压校验通过。

## 关键设计决定

- M06–M08 采用用户确认的建议映射；M03 仍按 D01-M03 原始编号记录。
- 每个隔离目标都校验容器、卷、UUID、端口和媒体根；失败目标与原始失败日志保留。
- 混合集成回归失败不计为产品缺陷，改用逐套件独立数据库复验。
- 3386 首次恢复与 3397 final2 都保留；最终以覆盖完整写作历史的 3397 为准。

## 运行与结果

- 初始候选 399 项 SHA-256：`e64d76758b50dfa4f235d5c631e5bbba7e93bde00351beccb82e88124c615e6d`；无 R6 输入漂移。
- Java 21.0.12.1；Node 22.23.2；MySQL 8.4.9；Flyway 012.11；JAR SHA `771a72e8...`；Web BUILD_ID `mB0BX6ovaStArA61zmdDR`。
- Node test/typecheck/lint/build 退出 0；知识规范化 1/1、音频 5/5、Quiz 原子性 2/2 通过。
- D01-M03.b/c 通过；3397 独立恢复和真实续学/幂等/重启通过；浏览器旧课播放与刷新恢复通过。
- 确认 P0：备份缺 `COMPLETE` 仍恢复 PASS；确认 P1：`review_result` 可 UPDATE。
- ZIP 独立解压校验 799/799 PASS。

## 未通过 / 未验证

- D01-M03.a NOT VERIFIED。
- M07 的过程中断、媒体复制中断、DB/媒体不一致和 API 失败可诊断性 NOT VERIFIED。
- D01 全量历史回归、旧 Demo 完整闭环、10C-2 全量重跑 NOT VERIFIED。

## 截图位置

浏览器验收证据为 `output/playwright/phase10d-final-r7/demo-playback.png`；截图在证据包中保留脱敏副本。

## 下一阶段依赖

先由 CORE 修复 P0/P1，再补齐 M03.a 与 M07 剩余场景，之后另开独立验收轮重跑门禁；不进入 10E。

## 2026-11-05 P0/P1 修复

- `scripts/data-transfer.py` 增加 restore 前置 `COMPLETE` 检查；`V012_12__review_result_immutable.sql` 增加 `review_result_no_update`。
- 单元测试验证缺失/不匹配 `COMPLETE` 拒绝；`QuizReviewIntegrationTest` 在全新隔离容器验证 UPDATE 被拒绝并迁移到 012.12。
- 证据位于 `qa/phase10d-final-r7-fix/evidence/`；临时容器已停止，数据卷保留。
- Phase 10D 结论仍为 **NO-GO TO 10E**，等待完整剩余门禁复验。
