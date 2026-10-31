# Phase 10C-2｜动态测验题集协议与真实分母 实施报告

> 2026-10-31更新：用户已授权分批提交、推送及本地部署，数据库已由009.15升级011.09，见[部署报告](PHASE_10C_DEPLOYMENT.md)。以下实施记录中的“未提交/未部署”描述保留为部署前状态；计划验收缺口仍以§5为准。

日期：2026-10-31（Asia/Shanghai）。绑定 HEAD：`49239c61f53caed0a996dbce9156c7c6db259dc7`（实施全程未提交；10C-1 未提交改动保持原状）。个人库（3308）与个人服务（3100/8085）全程只读未触碰；所有构建、服务、迁移、备份演练均在 `.local/phase10c2` 隔离副本与专用容器（`northstar-phase10c2-20261031a-*`，3307/3334/8175/8176/3195 回环）完成。

## 1. 改动了什么

| 领域 | 内容 |
| --- | --- |
| 协议（C02） | 新增 `QuizSets`（题集冻结投影：item/set 双层 SHA-256 哈希、1..100 题校验、默认集冻结）与 `QuizFault`；`QuizReviewController` 双协议：旧 `POST /quiz/attempts` 仅限冻结 Demo 三题（原路径/原 payload/原回执哈希），新 `POST /quiz/sets/{setId}/attempts`（protocolVersion `quiz-submit-v2`）按题集逐题校验选项、全部评分后单事务写入 run/answer/attempt/evidence/quiz_run_item/复习来源 |
| 数据库 | 新增 V011.01–V011.09：quiz 支持键、exercise_set、exercise_set_item、quiz_run 分母列（total/submitted/set/set_hash）、quiz_run_item 逐题快照（question_json 冻结 + item_hash）、旧三题 verified 回填、CHECK 收紧（total∈[1,100]、submitted=total、correct≤submitted）、完整性 FK、冻结守卫触发器（V011.09，demo 历史不可改写） |
| 报告（C03） | `ReportController` 重写为 `SUM(correct)/SUM(total)` 仅计核验 run（verified 子句校验行数一致）；响应新增 `verifiedRuns/unverifiedRuns/accuracy/note`、`quizScope`、逐轮明细；支持 lessonId/versionId/setId/from/to/purpose（UTC，from 含 to 不含；purpose 仅 quiz，否则 422） |
| 前端 | `QuizPanel` 重写：动态题数/ordinal 排序、已答进度与未答禁交、草稿作用域 `northstar:quiz:v2:{lessonId}:{versionId}:{setId}:{setHash}`、旧键兼容导入（成员+选项完全匹配才导入且不删旧键，否则隔离并保留查看/导出）、旧 outbox 按原 path/body 重试、历史用 run 快照渲染、提交前无 answerKey/explanation 泄露；`ReadingQuestion` 移除硬编码第 6 句，按 lesson.sentences 实际 sequence 展示来源句；`LearningReport` 展示真实分母、核验/未核验轮数、逐轮明细 |
| 备份 | `data-transfer.py`：schemaVersion 白名单加 `011.09`、INSERT 授权加 `quiz_run_item`、新增 `--phase10c2` 隔离模式；修复恢复流程对 V011.09 冻结守卫的兼容（见 §4） |
| 内容/阅读 | `ExerciseController` 移除 `-kp-please` 全局排除；`ContentPublication`/`ContentSeeder` 在内容初始化后 `QuizSets.freezeDefault` |
| OpenAPI | `/reports` 筛选与口径、`/quiz` 新响应、新增 `/quiz/sets/{setId}/attempts`、旧 `/quiz/attempts` 标注 legacy bridge |
| 测试基建 | `phase10c2_isolated.py` 新增 `prepare-tests/run-tests/serve/serve-restored/stop-serve/web-build`；`QuizScaleIntegrationTest`（12/100 题）、重写 `QuizReviewIntegrationTest` 双协议用例、`AudioIntegrationTest` 增加合成数据 `@AfterEach` 清理、pom surefire `runOrder=alphabetical`（消除跨类 DB 污染） |

## 2. 关键设计决定

1. 旧三题协议字节级保留（原 DTO 校验 3 题、原响应、原 payload_hash），仅冻结 Demo 使用；新协议为独立 DTO/operation，客户端 correctCount/total 不是权威输入。
2. 题面快照进 `exercise_set_item.question_json` + item_hash，历史渲染不回查现行内容；`quiz_run_item` 学习导出/恢复白名单覆盖，跨库续学后历史与报告口径一致。
3. verified 判定在后端由事务数据推导（quiz_run_item 数=total_count 且 submitted=total），不信任客户端标记；未核验历史（如孤儿行）不进分子分母。
4. 前端草稿/outbox 以 setHash 隔离：题集变化后旧草稿永不静默合并；丢响应重试复用原 eventId，不产生第二轮。
5. 恢复工具在数据导入前移除目标库守卫触发器、提交后按 `information_schema.TRIGGERS` 原文重建（守卫保护的是运行库，不应阻止合法恢复）。

## 3. 运行命令与结果（完整 argv/exit/log hash 见 `docs/handoff/evidence/phase10c2/execution-commands.jsonl` 与 `migrations/commands.jsonl`）

| 命令（经 `scripts/phase10c2*.py` 隔离执行） | 结果 |
| --- | --- |
| `migrations`（固定旧备份→V010→V011.09；空库 V001→011.09） | PASS（`migrations/upgrade-acceptance.json`、`empty-acceptance.json`：targetVersion 011.09、旧列逐 PK 逐值 exact、两次启动快照一致） |
| `mvn test`（35 项，含新规模测试；JDK 21，test 库启用） | PASS 35/35（`mvn-test-scale2-*.log`）；12 题 29ms、100 题 183ms、request 5303B/response 28101B，逐题明细 100/100 无截断 |
| `npm test` / `typecheck` / `lint` / `build`（隔离副本） | PASS（web-test/typecheck/lint/web-build-c2 日志） |
| `python3 -m unittest discover`（scripts/tests） | PASS（py-test 日志） |
| Demo 全闭环 Playwright（隔离 8175/3195，test 库头校验） | PASS 7 项（`browser-demo-loop.json`；截图 `output/playwright/phase10b2-demo/`） |
| QuizPanel 专项 Playwright | PASS 5 项（`browser-quiz-ui.json`；截图 `output/playwright/phase10c2-quiz/`） |
| `data-transfer backup --phase10c2` | PASS（48 表含 quiz_run_item 3 行；`backup-drill/`） |
| `data-transfer restore --phase10c2 --confirm-new-isolated` | PASS→`northstar_restore_20261030184748`，逐表行数核对通过（`backup-restore-acceptance.json`） |
| 恢复副本续学 + 重启 | PASS：基线 1 轮（verified、3/3、setHash 与原库一致）→ 再交一轮 → 重启后 2 轮全保留 verified；报告 6/6、accuracy 1.0、口径 note 正确 |
| 保全核对 | PASS：V010_01–06 六文件 SHA-256 与计划冻结值全部一致；旧表逐值对账 PASS；播放器五文件未列入任何 10C-2 命令（`preservation-acceptance.json`、`sha256-manifest.json`） |
| OpenAPI YAML 解析、`git diff --check` | PASS |

## 4. 期间发现并修复的问题

1. **跨测试类 DB 污染**：Audio/ContentPublication/MultiCourse 测试遗留数据破坏 Catalog 断言。修复：Audio 加 `@AfterEach` 清理其合成行（不削弱断言）+ surefire alphabetical 顺序（Catalog 在写库类之前）。
2. **五题集 422**：fixture option id 用裸 `a/b` 而提交值为全称；demo 内容包 option id 本就是全称。修正 fixture 与 demo 对齐。
3. **恢复工具 vs V011.09 守卫**：mysqldump 重建的守卫触发器 definer（migrator）对新库无权限，且 INSERT 守卫直接拒绝恢复冻结题集。修复：导入前对 definer 授目标库 DML+TRIGGER、记录并删除守卫、提交后重建（需 `DELIMITER //` 包裹含分号触发器体）。三次失败目标库按工具设计保留在隔离容器内（批量 DROP 被审批审核拒绝，未强行清理；不含个人数据）。
4. `Next.js rewrites` 在 build 期固化 API 端口：隔离 Web 需 `API_PORT=8175` 构建（已加入 runner `web-build` 动作）。

## 5. 验收条目结论

| 组 | 结论 |
| --- | --- |
| C02 数量（1/3/5/12/100） | PARTIAL：3/5/12/100 已测；1 题成功提交未单独验证 |
| C02 拒绝/原子性/幂等 | PARTIAL：已测漏题/外题/错选项/hash/协议/并发；首题、末题、回执前、beforeCommit 四类故障注入未完成，不据此宣称原子性验收通过 |
| C03 | PASS（1/3+4/5=5/8 精确聚合、混合历史、孤儿行不进分母、报告筛选与 note） |
| 浏览器 | PARTIAL：Demo 三题浏览器进度/草稿/重试通过；5/12/100题完整浏览器操作未验证，100题仅后端实测 |
| 迁移 | PASS（upgrade/empty 双路径 + 二次启动一致） |
| 保全 | PASS（V010 字节、旧表逐值、播放器文件无 10C-2 编辑记录） |
| 备份 | PASS（真实导出→新隔离恢复→续学→重启；非仅 JSON 解析） |
| 回归 | PASS（Demo 全闭环 7 项；240 次声学签收按计划不重做——播放器未改） |

## 6. 未解决问题与限制

1. 三次失败恢复目标库与两个 diag 库保留在隔离容器（审批审核拒绝批量 DROP）；如需清理请明确授权逐库删除。
2. `NORTHSTAR_TRANSFER_DEBUG=1` 会把 MySQL 错误行（含表名，不含数据/凭据）附在 FAIL 信息里；默认关闭。
3. 浏览器验收使用 Headless Chrome；真实麦克风、通知等系统能力未测（同 10C-1 口径）。
4. 个人库/个人服务仍为 009.15 + 旧构建；本阶段不部署（部署需单独授权窗口）。
5. 所有改动未提交 Git；阶段审核通过前不提交。

## 7. 下一步依赖

本阶段实现与已执行测试已交付，完整计划验收仍有上述缺口，不标为全项PASS。10D（错题关系）以本阶段冻结的 exercise_set/quiz_run_item 为前置。脱敏证据包：`output/review/northstar-phase10c2-sanitized-evidence.zip`（逐文件 SHA-256 + 校验脚本，排除个人数据/凭据/教材）已生成，校验方式见包内 `VERIFY.md`。
