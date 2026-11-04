# Phase 10D-D02 独立 QA 测试计划（QA-PREP 交付）

日期：2026-11-01（Asia/Shanghai）。角色：独立 QA（非 CORE 开发者）。状态：**QA-PREP 完成；QA-EXEC 未开始，全部 D02 条目 BLOCKED_BY_CORE**。

- QA worktree：`worktree-10d-d02-qa`，基线 = Git `a5084cb`（D01 门禁冻结候选 = `a5084cb` + 92 文件未提交整改，清单哈希 `d90dfbc122300e10b3c70065a6e0349afd818161ba42f6460c9e2cd6c66fac36`）。
- CORE D02 候选：未提供。`concept_review_card`/`concept_review_source`/`concept_review_result`、`conceptReviews` API、自评接入在当前源码中**完全不存在**（已静态核对，见 §1.2）。本计划不因设计文档已有接口名称而假设接口已实现。
- 本轮只交付测试方案与原创 fixture 规格；不编写依赖未冻结 D02 Schema 的最终 SQL/Java 工具，不运行任何 D02 集成测试。

## 0. 结论标记约定

| 标记 | 含义 |
| --- | --- |
| PASS | 实际运行且通过，绑定候选 SHA-256、命令退出码与 DB 前后状态 |
| FAIL | 实际运行且复现缺陷（不得通过修改测试预期消除） |
| BLOCKED_BY_CORE | 依赖 CORE 未冻结的 Schema/迁移/API/复习逻辑 |
| NOT VERIFIED | 有计划与工具但本轮未实际运行 |

**未完成实际数据库集成测试前，D02 不得宣布 PASS。**

## 1. 依据与现状核对

### 1.1 已读文档

- D01 门禁报告 `docs/qa/phase10d/10D_QA_D01_RELEASE_GATE.md`：七项 D01 缺陷修复 PASS；V012_08（复合 FK `fk_occurrence_revision_concept`）关闭 R-QA-011；R-QA-010（conceptReviews）BLOCKED_BY_CORE；D02 全部 NOT VERIFIED。
- `docs/phase10/10D_IMPLEMENTATION_PLAN.md` §4：D02 数据与接口契约（本计划的契约基线）。
- `docs/phase10/03_TARGET_DATA_MODEL.md` §5、`docs/phase10/08_TEST_AND_ACCEPTANCE_PLAN.md` D02 行、`docs/phase10/10C_2_IMPLEMENTATION_PLAN.md`。
- `docs/progress/PHASE_10D_1.md` 与 10C-2 报告（幂等/回执/历史核验既有结论）。

### 1.2 现有源码事实（QA-PREP 静态核对）

| 对象 | 现状 | 对 D02 的约束 |
| --- | --- | --- |
| `review_item`/`review_source`（V004/V007） | 旧句卡链已存在；source 以 attempt 为 PK、保持同句上下文 | D02 新卡不得迁走/重置旧卡（§5 E 组） |
| `review_result`（V007） | `event_id` PK→`command_receipt`；`UQ(item_id,previous_row_version)` | D02 `concept_review_result` 预期同构：event PK + UQ(card,previous_rowVersion) |
| `QuizReviewController.rate` | 同事务：回执重放优先 → `SELECT ... FOR UPDATE` → owner/rowVersion/到期/翻卡校验 → INSERT result → UPDATE card → 回执存响应；`DuplicateKeyException` 后重放；异 payload 409 `IDEMPOTENCY_CONFLICT` | D02 评价必须复用同一命令事务模式；rating 当前仅 `again|good` 且必须 `answerRevealed` |
| `SimpleScheduler` | again=now+1min；good=now+(1<<min(reps,5)) 天（1/2/4/8/16/32，上限 32 天） | D02 调度预期复用；hard/easy 本期无算法，不得静默映射为 good |
| `KnowledgeSources.record` | 服务端按冻结 `exercise_knowledge` 冻结来源，不信客户端 conceptId；错误 attempt 的 target 才应触发概念卡 | 多来源聚合的数据来源链 |
| D02 三表与 `conceptReviews` API | **源码与迁移中均不存在** | 全部 D02 条目 BLOCKED_BY_CORE |

### 1.3 D02 契约基线（10D 计划 §4，冻结时逐条复核）

- `concept_review_card`：opaque id、owner_key=`local`、concept_id、prompt_kind=`meaning_recall`、protocol_version=`concept_self_v1`、scheduler_version=`simple_v1`、due_at/reps/row_version/status；UQ(owner,concept,prompt_kind,protocol)。
- `concept_review_source`：PK(card_id,attempt_id,occurrence_id)；复合 FK 保证 card 概念与 attempt_knowledge 概念一致；只从真实错误 attempt 的 target 追加；support 不建卡。
- 首次错误建卡 due=服务端 now；后续新错误追加来源并一次更新 due=min(旧due,now)、reps=0、row_version+1；event 重放不得再次重置。
- `concept_review_result`：event PK→receipt、card FK、previous/next due、previous rowVersion/reps、rating/origin/scheduler；UQ(card,previous_rowVersion)；仅追加。
- API：`GET /api/v1/concept-reviews?due&cursor&limit`、`/{id}`、`/{id}/answer`、`/{id}/sources`、`/{id}/results`；评价带 eventId/rowVersion/rating/answerRevealed/客户端日期；服务端 Clock 决定 now。

## 2. 隔离要求（QA-EXEC 前置）

1. 独立 worktree（本文档所在 worktree）；QA 不改 CORE 主工作树业务代码与 V012 迁移。
2. 独立 MySQL：10D 命名空间专用容器/schema（沿用 D01 容器纪律：写前核验容器 ID/标签/server UUID/端口/schema；不复用含负例残渣的共享测试库；不复用 `prepare-tests` 的 DROP 行为）。**个人 3308、个人服务 3100/8085、现有卷全程不连接。**
3. 独立浏览器 profile、独立 API/Web 端口与媒体目录；Playwright 只连隔离服务，先核验测试库响应头。
4. 证据目录独立：`qa/phase10d2/`（fixture/sql/log）+ `docs/qa/phase10d/`（报告）；失败现场保留，不清理。
5. 沿用 D01 门禁 §6 运行顺序：真实迁移/套件先于破坏性负例；容器重启后重设 `log_bin_trust_function_creators=1`；快照 tag 每版本唯一。

## 3. 原创 Fixture 规格（不依赖新接口，本轮可先行准备）

复用 D01 原创合成 fixture `qa/phase10d/fixtures/concepts_course_a.json`/`concepts_course_b.json`（两课不同文本、许可字段明确为合成测试），D02 追加以下登记与事件要求。**所有 attempt 必须经真实 API 提交流程产生，禁止 INSERT 冒充。**

| ID | 内容 | 用途 |
| --- | --- | --- |
| F-01 | 课 A、课 B 各含共享概念 `qa-con-bank-fin`（vocabulary, bank 金融义项）的 target 关联；经真实 API 制造两条真实错误 attempt（如 A 课听写 token 不匹配 + B 课阅读错误选项） | 多来源聚合的两条独立来源 |
| F-02 | 第三条合法来源：同一概念在课 A 或课 B 的第三个 target 题上再产生一次真实错误（quiz 或另一阅读题），attempt_id/occurrence_id 均不同 | 验证三来源独立追加 |
| F-03 | 同形异义 `qa-con-bank-riv`（bank 河岸）在课 B 的错误 attempt | 验证不并入金融卡 |
| F-04 | support 角色关联（attempt 冻结含 support 但无 target 错误） | 验证 support 不触发卡 |
| F-05 | 课 C（合成原创）：正常产生来源后撤回课程版本 | R-QA-010 受限来源场景 |
| F-06 | 每张卡产生前的旧学习记录基线快照（review_item/source/result、learning_evidence、quiz_run、attempt 全字段） | E 组对账基线 |

已落盘文件（QA-PREP，均为原创合成数据，JSON 语法已校验）：

- `qa/phase10d2/fixtures/d02_registration_course_a_support.json`：F-04 support-only 练习 `qa-ex-support-only`（无 target）。
- `qa/phase10d2/fixtures/d02_registration_course_b_bank.json`：F-03 河岸义项 target 练习 `qa-ex-read-b-bank`。
- `qa/phase10d2/fixtures/d02_registration_course_c_withdraw.json`：F-05 撤回课 C（复用 so-that 概念，前置要求课 C 合成内容经正式内容管线导入）。
- `qa/phase10d2/fixtures/d02_review_events.json`：EV-A1/A2/B1（bank-fin 卡三来源）+ EV-B2（同形异义）+ EV-C1（撤回前来源）真实 API 事件计划与撤回后置动作。
- `qa/phase10d2/sql/legacy_protection_baseline.sql`：E/C 组基线与对账 runbook（仅引用既有表，S0–S3 四时间点快照 + CHECKSUM 快探 + 全行 dump）。
- `qa/phase10d2/tools/check_candidate_readiness.sh`：CORE 候选就绪检查（只读；当前实测 NOT READY，5 项缺失，见执行记录）。

登记文件引用的列名在 QA-EXEC 时仍须按冻结 Schema 逐项复核；如冻结后列名变化，以冻结 Schema 为准修订 fixture。

## 4. D02 独立测试矩阵

所有条目当前状态均为 **BLOCKED_BY_CORE**（等待冻结候选 + 真实 Schema/迁移 + OpenAPI + fixture 落盘授权）。

### 4.1 A 组：多来源聚合

前置：F-01/F-02/F-03/F-04。DB 断言为主，接口断言为辅。

| ID | 用例 | 通过标准 |
| --- | --- | --- |
| D02-A01 | 两课两条真实错误 + 第三合法来源（F-01/F-02） | 一张卡、三条来源；`concept_review_source` 恰 3 行，card 概念一致 |
| D02-A02 | 重复触发同一 attempt/同一错误重放 | 来源不重复（PK 幂等）、不覆盖旧行；卡 due/reps/row_version 不因重放再次重置 |
| D02-A03 | F-03 同形异义错误 | 河岸错误不进入金融卡；两张卡各自独立计数 |
| D02-A04 | 全部来源行回链 | 每条 source 均有真实 `exercise_attempt` + `attempt_knowledge`(role=target) + `knowledge_occurrence`，无孤儿行 |
| D02-A05 | 来源概念一致性负例 | 直接 SQL 插入 card 概念 ≠ attempt_knowledge 概念的 source 行被复合 FK 拒绝（1452） |
| D02-A06 | 来源版本一致性负例 | source 引用其他版本/其他 revision 的 occurrence 被复合 FK/服务校验拒绝 |
| D02-A07 | 合法新版本/新修订 | 登记新版 occurrence、新修订后，既有卡来源关系与历史 result 逐值不变（不重写历史） |
| D02-A08 | F-04 support attempt | 不建卡、不追加来源 |

### 4.2 B 组：CAS 并发与幂等（必须核对 DB，不得只断言 HTTP 状态）

前置：单卡 rowVersion=v0。并发用两个独立连接/HTTP 会话真实竞争，不用 mock。

| ID | 用例 | 通过标准（DB 断言） |
| --- | --- | --- |
| D02-B01 | 两个不同 event 同时评价同一 rowVersion | 恰一个成功；`concept_review_result` 恰 1 行；卡 row_version=v0+1 恰一次；败方 409 且卡/回执/result 无第二行 |
| D02-B02 | 相同 event 并发重试（同 payload） | 两响应均成功且内容一致（同一 nextDue/rowVersion）；result、receipt、卡更新各恰 1 次 |
| D02-B03 | 相同 event、异 payload | 409 `IDEMPOTENCY_CONFLICT`；无新增 result/卡变化 |
| D02-B04 | 旧 rowVersion 延迟到达（先成功一次再发 v0） | 409；卡保持 v0+1 状态；无新 result 行；reps/due 不回退 |
| D02-B05 | 成功提交后丢失响应，原 event 重试 | 重试返回原响应（回执重放）；DB 无第二次状态变化 |
| D02-B06 | 事务提交前失败（评价事务内注错） | 全或无：无 result、无 receipt、卡 due/reps/row_version 原值 |
| D02-B07 | INSERT result 后、提交前失败（在 result 之后注入异常） | result 回滚、receipt 回滚、卡更新回滚；重试可完整成功恰一次 |
| D02-B08 | 新错误来源追加与自评并发竞争同一卡 | 通过同卡锁串行：两个操作都生效且 row_version 连续递增，无静默覆盖；最终 due/reps 与两操作的串行序一致 |
| D02-B09 | 重启后状态核对 | 容器/应用重启后 due/reps/row_version/result/receipt 与重启前逐值一致 |

### 4.3 C 组：自评真实性

前置：到期卡 + 翻卡（answerRevealed）。每例后核对 DB 与报告接口。

| ID | 用例 | 通过标准 |
| --- | --- | --- |
| D02-C01 | again | next_due=服务端 now+1min（容差≤调度精度）；reps=0；row_version+1 |
| D02-C02 | good（reps=0..5） | next_due=now+1/2/4/8/16/32 天逐档正确；reps+1；reps≥6 时上限 32 天 |
| D02-C03 | hard / easy | 按 10D 计划 §4.2 本期不支持：显式拒绝（4xx），卡状态/result/回执零变化。**若 CORE 实现了 hard/easy，须给出算法依据并单独验证，不得默认用 good 算法映射（契约问题 Q-D02-01）** |
| D02-C04 | 未翻卡（answerRevealed=false）或伪造 rating | 拒绝；零状态变化 |
| D02-C05 | 自评后学习数据对账 | `exercise_attempt`、`learning_evidence`、`quiz_run`、`quiz_run_item` 行数与自评前一致；不产生任何客观 attempt |
| D02-C06 | 自评后报告对账 | correctCount、客观测验分母（verifiedRun 口径）不变；报告接口无自评来源计数混入 |
| D02-C07 | 结论字段检查 | 卡/结果/报告不得出现"延迟保持/迁移能力/掌握度"等未测量结论字段；客观复测仍显示"未验证" |

### 4.4 D 组：来源权限 R-QA-010（重要验收门槛）

前置：F-01/F-05（公开课 A/B、撤回课 C）。

| ID | 场景 | 通过标准 |
| --- | --- | --- |
| D02-P01 | 公开可见课程来源 | 列表/详情/sources 正常返回原文上下文 |
| D02-P02 | 旧版合法来源 | 旧版本（已发布、未撤回）的来源正文正常返回，保留原 lesson/version/sentence 身份 |
| D02-P03 | 撤回课程来源 | 只返回允许的受限占位（id/scope/versionId/lessonId/日期 + restricted 标记），不含正文/讲解/选项/音频 |
| D02-P04 | 缺失许可正文 | 无许可内容不出现在任何来源响应字段（含 snapshot_json 派生字段） |
| D02-P05 | 聚合泄露 | lessonCount/firstSource 等聚合字段不因受限来源暴露受限正文、标题或可推断原文的文本 |
| D02-P06 | sources 接口负例 | 响应无 storageKey、无受限音频 URL；直接构造受限资源请求被拒 |
| D02-P07 | 非法组合 | 不存在的 course/version/card 组合、越权 occurrence 组合均 404/422，不返回部分内容 |
| D02-P08 | 历史身份保留 | 撤回后卡与历史 result 保留原事件身份与时间；answer/新评价按可见性拒绝；原成功回执幂等重放仍返回原响应 |

### 4.5 E 组：旧学习记录保护

方法：F-06 基线快照 → 新概念卡/来源/结果全部产生后再次快照 → 逐值对账。

| ID | 对账对象 | 通过标准 |
| --- | --- | --- |
| D02-H01 | 旧 `review_item` 全行 | id/due_at/reps/row_version/status/target_key 等逐值不变；无重置、无迁移 |
| D02-H02 | 旧 `review_source` / `review_result` | 全行逐值不变；无重复回执、无新 result |
| D02-H03 | `learning_evidence`、`quiz_run`、`quiz_run_item` | 行数与内容逐值不变 |
| D02-H04 | 历史 attempt 与 Knowledge 来源 | `exercise_attempt`、`attempt_knowledge`（含 source_json/sha256）逐值不变 |
| D02-H05 | 新旧卡共存 | 旧句卡可继续正常评价（含 CAS 语义），新概念卡加入不改变旧卡任何行为 |

### 4.6 F 组：备份与迁移

| ID | 用例 | 通过标准 |
| --- | --- | --- |
| D02-M01 | D01 V012_08 冻结基线 | V012_01–V012_08 文件字节不变（SHA-256 复算）；Flyway history 连续 |
| D02-M02 | 新增 D02 迁移 | 独立建表单元（card/source/result 分文件）；history 登记正确；不回填历史、不生成复习数据 |
| D02-M03 | `location_guard` 生成列恢复 | data-transfer 恢复列集剔除 STORED GENERATED 列（D01 修复延续）；恢复后生成列值正确重算 |
| D02-M04 | 新表完整恢复 | card/source/result 及 attempt_knowledge 全行恢复，媒体 hash 一致 |
| D02-M05 | 故障恢复与重复启动 | 每个主要 DDL 边界中断可识别；恢复目标可从头完成；两次启动快照一致 |
| D02-M06 | 跨概念复合 FK 负例 | 在专用隔离 schema 执行破坏性负例（不依赖共享测试库残留）：非法 concept/revision 组合插入被拒 |
| D02-M07 | 恢复后续学 | 恢复副本上实际执行概念自评与旧句卡评价（含幂等重放），重启后逐值核对 |
| D02-M08 | 导出/备份分类 | 新表进入备份与 ExportController 分类；白名单同步 |

## 5. 对账 SQL 计划（Schema 冻结后落盘）

沿用 D01 `qa/phase10d/sql/invariant_checks.sql` 风格，在 `qa/phase10d2/sql/` 新增（列名以冻结 Schema 为准，本轮不预写）：

- I-D02-01 无孤儿 source（每行回链真实 card/attempt_knowledge/occurrence，概念一致）。
- I-D02-02 result 与卡状态一致性（next_due/previous_rowVersion 与当时卡值对得上）。
- I-D02-03 同卡 result 的 previous_rowVersion 无重复（UQ 兜底验证）。
- I-D02-04 自评零副作用（自评 event 数 = 新增 exercise_attempt 数为 0）。
- I-D02-05 旧表逐值对账（E 组）：基线表 join 比对，diff=0。
- I-D02-06 受限来源不泄露（sources 派生表无撤回正文字段）。

## 6. QA-EXEC 前置条件与顺序

CORE 须提供：固定候选 SHA-256 清单、真实 Schema 与迁移、OpenAPI、原创测试数据、运行说明（含隔离端口/容器/schema 标识）。

执行顺序：
1. 校验候选 SHA 与隔离环境身份（容器/UUID/端口/schema/响应头版本）。
2. 迁移正例与 F 组结构负例。
3. fixture 落盘与登记 + A 组多来源聚合。
4. B 组 CAS/幂等（含故障注入）+ C 组自评真实性。
5. D 组 R-QA-010 权限矩阵（API + DB 双重断言）。
6. E 组旧数据对账。
7. 备份/恢复演练（M03–M07）+ 旧回归（QuizScale、QuizReportR1、KnowledgeSources 复跑）。
8. Playwright 浏览器流程（多源卡、双 Tab CAS、断网/丢回执、撤回受限、旧新卡分组）。
9. 汇总 EXECUTION/BUG/ACCEPTANCE 与脱敏证据包。

## 7. 当前阻塞清单（QA-PREP 时点）

| 项 | 状态 |
| --- | --- |
| QA-PREP 时点：D02 三表/迁移/OpenAPI/复习逻辑 | 已解除（CORE 已在工作树落地候选；QA 已快照冻结并实测） |
| QA-EXEC 第一轮结论 | 5 项缺陷已由 CORE R1 修复（见缺陷报告附注） |
| QA-EXEC 第二轮结论 | R1 冻结候选（27 文件+JAR 独立复验）在 QA 独立库全量 PASS；A/B/C/D/E 组实测通过，F 组 M03–M08、B08/B09、浏览器流程 NOT VERIFIED |
| 验收结论 | **CONDITIONAL PASS**（见 `10D_D02_QA_ACCEPTANCE.md` 附加条件） |

## 8. 证据与脱敏要求

- 每条命令记录时间（北京/UTC）、cwd、argv（脱敏）、原始退出码、日志 SHA-256；失败原件保留。
- DB 断言保留前后状态查询输出（脱敏后仅含合成数据）。
- 证据包 `output/review/northstar-phase10d2-qa-sanitized-evidence.zip`：白名单收录本计划、fixture、SQL、日志、对账摘要、SHA-256 清单与独立校验脚本；排除 .env/密码/个人数据；逐文件记录 hash。
