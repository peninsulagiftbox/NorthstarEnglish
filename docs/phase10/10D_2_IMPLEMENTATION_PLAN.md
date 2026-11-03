# Phase 10D-2 实施计划（待审核）

日期：2026-11-01（Asia/Shanghai）。状态：**仅计划；未经批准不得实施**。D02 全部条目 NOT VERIFIED，R-QA-010 维持 BLOCKED_BY_CORE，本计划为关闭它而制定。

## 1. 执行边界与基线核对

本轮授权：代码开发与隔离环境测试。不授权个人库（3308）迁移/写入、个人服务（3100/8085）部署、Git 提交合并推送、自动开始 10E。所有迁移、集成测试与浏览器验证仅使用 `.local/phase10d` 隔离副本与专用容器（回环端口，`--phase10d` UUID 守卫），沿用 D01 门禁报告的隔离纪律（准备顺序、`log_bin_trust_function_creators`、快照 tag 参数化）。

D01 基线已实时核对（本轮只读检查）：

- Git HEAD=`a5084cb`；工作区含 7 个 tracked 修改与 2 个 untracked（V012_08、D01 门禁报告），与 D01 冻结候选 92 文件清单一致；`V012_01`–`V012_08` 实际 SHA-256 与 `qa/phase10d/evidence/candidate-sha256.txt` 逐文件匹配（V012_08=`73ed9c27…`，清单哈希 `d90dfbc1…`）。
- D01 七项修复与 R-QA-011（V012_08 复合外键）均在工作区；10C-2-R1 的 `QuizSets.verifiedRun`、`ReportController.quizFilter` 绑定参数仍在源码；`data-transfer.py` 恢复列集动态剔除 STORED 生成列（防 3105）已在。
- 隔离环境身份、Flyway 状态在每次测试前按 D01 §6 顺序重新核验；不使用只含 HEAD 的旧代码副本。

## 2. Schema 设计（新迁移 V012_09–V012_11，不改 V001–V012_08 任何字节）

以 03_TARGET_DATA_MODEL §5 为准，结合实际 V012_07/V012_08 Schema 落地：

| 迁移 | 内容 |
| --- | --- |
| `V012_09__concept_review_card.sql` | 新建 `concept_review_card` |
| `V012_10__concept_review_source.sql` | `attempt_knowledge` 增加唯一索引；新建 `concept_review_source` |
| `V012_11__concept_review_result.sql` | 新建 `concept_review_result`（评价历史，追加不可变） |

### 2.1 concept_review_card

- 列：`id CHAR(36) ascii_bin PK`、`owner_key VARCHAR(16) NOT NULL DEFAULT 'local'`、`concept_id VARCHAR(64) ascii_bin NOT NULL`、`prompt_kind VARCHAR(24) NOT NULL`、`protocol_version VARCHAR(24) NOT NULL`、`status VARCHAR(24) NOT NULL DEFAULT 'pending'`、`due_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))`、`reps INT NOT NULL DEFAULT 0 CHECK(reps>=0)`、`row_version BIGINT NOT NULL DEFAULT 1`、`scheduler_version VARCHAR(24) NOT NULL DEFAULT 'simple_v1'`、`created_at`、`updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))`。
- 约束：`UQ(owner_key, concept_id, prompt_kind, protocol_version)`——同一概念同一协议不产生重复卡；不同 senseKey 是不同 `knowledge_concept` 行，天然不混卡；课程版本不是卡身份的一部分，版本变化不改卡。`CHECK prompt_kind IN ('meaning_recall')`（D02 仅登记一种：正面义项解释、翻卡回忆术语）；`CHECK status IN ('pending')`；`CHECK protocol_version IN ('concept_review_v1')`。
- FK：`concept_id → knowledge_concept(id)`；`INDEX(status, due_at, id)`。
- 不建 `lesson_id`/`sentence_id` 列：跨课卡不以课/句为主锚点（03 文档明确）。

### 2.2 concept_review_source

- 列：`card_id`、`attempt_id`、`occurrence_id`、`exercise_id`、`version_id`、`concept_id`，全部 `NOT NULL`，`PK(card_id, attempt_id, occurrence_id)`（满足并强于 `UNIQUE(card_id, attempt_id, occurrence_id)`）。
- 关键外键：先在 `attempt_knowledge` 上补 `UQ(attempt_id, occurrence_id, exercise_id, version_id, concept_id)`（V012_10，仅加索引不改数据），然后 source 建立 `FK(attempt_id, occurrence_id, exercise_id, version_id, concept_id) → attempt_knowledge(...)`。这保证每条 source 必然来自真实 attempt_knowledge 快照，且其 `concept_id` 与引用行完全一致——不是只检查 attempt 与 occurrence 各自存在；再与 `card_id → concept_review_card(id)` 组合，source 与卡的 Concept 一致性由数据库强制（跨概念引用 1452 拒绝）。
- 版本/练习上下文经由 attempt_knowledge → exercise_knowledge → occurrence 的既有复合 FK 链锁定，source 不再冗余 lesson_id。
- 不迁移任何旧 `review_item`/`review_source`/`review_result` 数据；旧句卡与新卡并存于不同表。

### 2.3 concept_review_result

- 列与 V007 `review_result` 同构：`event_id PK → command_receipt(event_id)`、`card_id FK`、`rating CHECK IN ('again','good')`（现有协议仅两档，不扩大）、`origin CHECK='self_rating'`、`scheduler_version='simple_v1'`、`previous_due_at`、`next_due_at`、`previous_row_version`、`client_occurred_at`、`recorded_at`；`UQ(card_id, previous_row_version)` 提供数据库级 CAS 保证。
- 历史评价不可被普通业务请求重写：无 UPDATE/DELETE 路径；触发器沿 V012_07/V012_08 先例追加 no_update/no_delete 守卫（置于 V012_11）。

## 3. 来源生成规则（D02-B）

沿用现有错题复习原则，协议版本 `concept_review_v1` 写入卡与文档：

- 资格由服务端判定：仅当一次 `exercise_attempt` 失败（`correct=FALSE`），且同一事务内 `KnowledgeSources.record` 冻结的 `attempt_knowledge` 行 `role='target'` 时，为该 `(attempt, occurrence, concept)` 生成 source。`support` 角色、浏览、播放、收藏、打开详情、暂停、跳过一律不生成来源，不产生"已完成学习"。
- 入口：在听写/阅读/quiz 三条 attempt 提交事务内、`KnowledgeSources.record` 之后追加 `ConceptReviewSources.record(db, …)`（新类，`local.northstar.knowledge` 包）。客户端传入的任何 conceptId 均被忽略，来源只从服务端冻结快照推导。
- 卡片处理：卡不存在则创建（`due_at=UTC_TIMESTAMP(3)` 立即到期）；卡已存在则**只**插入 source，不改 `due_at/reps/row_version/status`——来源追加不重置调度，调度只由自评 CAS 推进。
- 幂等：整个 attempt 提交已在 `command_receipt` 回执事务内，同 eventId 重放返回首次响应、不重复执行；source PK `(card_id, attempt_id, occurrence_id)` 兜底防重复行；同 occurrence 重复处理零新增。无内存事件队列，来源与 attempt 同一事务原子提交。

## 4. 复习调度协议与 CAS/回执事务（D02-C）

- 复用 `SimpleScheduler.next`（again=+1 分钟；good=1/2/4/8/16/32 天，按既往 good 次数）与旧 `/reviews/{id}/results` 的回执事务框架，`scheduler_version='simple_v1'`。旧句卡代码与 `simple_v1` 计算规则零改动。
- `POST /concept-reviews/{id}/results`（eventId, rowVersion, rating, answerRevealed, clientOccurredAt）单事务流程：① 回执重放/冲突判定；② `SELECT … FOR UPDATE` 校验卡存在、owner='local'、status='pending'、rowVersion 匹配、answerRevealed；③ 服务端时间计算 `next`；④ INSERT `concept_review_result`（`UQ(card_id, previous_row_version)` 数据库级 CAS）；⑤ 条件 UPDATE 卡 `WHERE id=? AND row_version=?`；⑥ 写回执与响应 JSON；⑦ 统一提交，任一步失败整体回滚。
- 并发行为：两请求同 rowVersion，FOR UPDATE 串行化后后者 rowVersion 不匹配 → 409 CAS 冲突，不重复计次、不丢结果；即使绕过行锁，`UQ(card_id, previous_row_version)` 也保证最多一个版本推进。同 eventId 同 payload 返回首次结果；同 eventId 异 payload 409 幂等冲突（既有 `commands.command` 语义）；"已提交但响应丢失"的重试走回执重放路径，专门测试。

## 5. 自评与客观成绩分离（D02-D）

自评只写 `concept_review_result` 与卡调度状态。代码与响应中不存在任何路径让自评生成 `exercise_attempt`、`quiz_run`、correct 计数或报告正确率；前端不展示任何掌握率百分比，明确提示"本次是复习自评，不代表客观测验成绩"。客观复测仍必须通过真实 ExerciseAttempt（并经 attempt_knowledge 回链来源）；24h/7d 保持与迁移评量留给 10F。

## 6. 内容权限矩阵（D02-E，关闭 R-QA-010）

复用 `KnowledgeController` 的 `VISIBLE = availability='available' AND publication_state='published' AND (demo OR license confirmed)` 谓词，单一出处共用：

| 内容状态 | 来源列表/详情返回 |
| --- | --- |
| 已发布且许可 confirmed（或 demo） | 完整来源：课程标题、句子序号/正文（sentence scope）、attemptId、练习、时间 |
| 旧版仍 published/available | 同上，按实际版本返回 |
| 已撤回 / 许可未确认 / 课程不存在或非法跨课引用 | 保留 `{sourceKey, attemptId, occurrenceId, lessonId, versionId, visible:false, restricted:true}` 身份与状态；删除标题、正文、题面、答案、usage、任何媒体与 storageKey/URL |

- 来源列表与 due 聚合计数均在 SQL 层带 VISIBLE 过滤：受限来源不计入可见 sourceCount/firstSource，不通过数量或聚合字段泄露关系。不依赖前端隐藏；不做第二个宽松实现。
- `GET /concept-reviews/{id}` 概念名/义项解释来自 `knowledge_concept_revision`（confirmed 最新版），属本地原创登记内容，可展示；但不携带受限出现位置的正文。

## 7. API 设计（D02-F，路径与既有 `/api/v1` 风格一致）

| 端点 | 语义 |
| --- | --- |
| `GET /api/v1/concept-reviews/due?all=&cursor=&limit=` | 分组所需卡片列表；`ORDER BY due_at,id` 稳定游标（1..100，默认 20）；仅 owner='local'、status='pending'；每卡带 due/reps/rowVersion/promptKind/concept（displayName、senseKey、kind、解释摘要）与 visibleSourceCount |
| `GET /api/v1/concept-reviews/{id}` | 单卡 + 调度状态 + 概念/最新 confirmed 修订（prompt 与翻卡内容）+ 404 语义 |
| `GET /api/v1/concept-reviews/{id}/sources` | §6 权限矩阵过滤后的来源分页（游标） |
| `POST /api/v1/concept-reviews/{id}/results` | §4 CAS 自评；错误响应：422 校验、409 CAS/幂等冲突（Problem JSON 携带 code） |
| `GET /api/v1/concept-reviews/{id}/results` | 自评历史（追加只读） |

旧 `/reviews/*` 端点与响应结构完全保留；不同概念卡之间无任何共享状态。`docs/openapi.yaml` 同步新增 5 个 operation；`apps/web/src/lib/api/conceptReviews.ts` 新增类型。全部查询 JDBC 绑定参数（沿用 R1 的 `CAST(? AS BINARY)` 标识比较经验）。

## 8. 前端复习体验（D02-G）

不重构整体 UI，仅扩展复习页：

- `ReviewQueue` 增加句卡/概念卡两组分区与各自到期数量；新增 `ConceptReviewCard` 组件（复用 `ReviewCard` 的 outbox/连点锁/重试模式，key=`northstar:concept-review:{id}`）。
- 卡面：概念名称+义项（kind/senseKey 中文标签复用 `knowledgeKindName`），正面义项解释，翻卡显示术语；自评按钮（还不会/记住了）与"本次是复习自评，不代表客观测验成绩"提示。
- 多来源列表：课程与句子链接（回到原课 tab/attempt 深链，复用旧卡模式）；受限来源显示"内容不可用（课程已撤回或无访问权限）"占位，不渲染正文。
- 状态齐全：loading/success/error/empty（无来源、加载失败、CAS 冲突、空队列分别呈现）；刷新后按 rowVersion/due 正确重渲染；断网 outbox 重试与连点防重沿用既有机制。不显示任何掌握率百分比。

## 9. 迁移、备份与恢复（§10）

- `data-transfer.py` schema 白名单追加 `012.09/012.10/012.11`；恢复端继续按 information_schema 动态剔除 STORED 生成列（`location_guard` 回归保持覆盖）。新表无生成列、无循环 FK（source→card 与 source→attempt_knowledge 均单向），恢复顺序无环。
- `ExportController`：新三表自动进入全量导出（`tables()` 全表 dump）；不属于 CONTENT 字节比对集（学习数据），import-preview 对账按学习表既有规则处理，需在测试中确认新表结构漂移会被检出。
- `phase10d_isolated.py` 的 prepare-tests/授权清单补新表 DML 权限（仅隔离测试库）。
- `scripts/deploy-phase10d.py` 目标版本仍指向 012.07：本轮随候选代码同步为最新迁移号并加入部署准备清单，但**不运行任何个人部署**。

## 10. 隔离测试与 D02 验收矩阵

测试主体：新 `ConceptReviewIntegrationTest`（真实隔离 MySQL，扩展 D01 的 A/B/C 原创课程夹具）+ 迁移/恢复演练 + Web 测试 + Playwright。旧句卡对账沿用"旧表逐值对比"方法。

| 验收项 | 覆盖方式 |
| --- | --- |
| D02-01/02 | 课程 A、B 真实错误 attempt → 同一卡、Source A/B 独立可回溯；第三个 attempt 追加 Source C，A/B 不变 |
| D02-03 | 同 eventId 回执重放 + 同 (attempt,occurrence) 重复处理：source/card/计数零新增、dueAt 不重置 |
| D02-04/05/06 | bank 两义不混卡；跨概念/跨版本非法 source 引用 1452/422 拒绝 |
| D02-07 | 两线程同 rowVersion 并发自评：恰一成功、另一 409，reps 只 +1，结果不丢 |
| D02-08/09 | 同 event 同 payload 重放零新增；异 payload 409 |
| D02-10 | 事务中途注错（result 后、卡更新前等）：零半记录 |
| D02-11/12 | 自评后 due/reps/rowVersion 符合 simple_v1；服务重启快照一致不漂移 |
| D02-13/14 | 旧 review_item due/reps/row_version 与旧 review_result 逐值不变 |
| D02-15 | 自评后无新 exercise_attempt/quiz_run/correct 变化 |
| D02-16/17 | 撤回课后来源接口仅受限元数据；聚合计数不含隐藏来源；无 storageKey/正文/音频 |
| D02-18/19 | Playwright：来源列表、受限占位、自评/刷新、断网重试与连点不重复评价、双 Tab CAS 冲突 UI |
| D02-20 | `--phase10d` 备份→恢复→逐表逐值对账（含卡片/来源/结果/调度）→恢复副本真实自评+旧句卡复习+重启一致；迁移走"旧备份升级 + 空库"双路径与 DDL 中断演练；媒体 hash 核验 |

回归范围：Java 单元+真实 MySQL 集成（0 skipped）、10C 动态测验/报告、10D-1 概念/来源/修订、Demo 完整闭环、Web typecheck/lint/test/build、Python unittest、Playwright。真实命令、退出码、候选 SHA-256、原始日志归档 `docs/handoff/evidence/phase10d2/`。

## 11. 交付物

`docs/progress/PHASE_10D_2.md`、`docs/progress/PHASE_10D.md`、`docs/handoff/evidence/phase10d2/`、`output/review/northstar-phase10d2-sanitized-evidence.zip`（脱敏：源码快照+SHA-256、新迁移 SQL 原文、D02 测试代码、原创跨课 fixture、CAS/幂等日志、可见性正反例、旧句卡与新表对账、浏览器截图、执行清单、可独立运行验证脚本；不含私人 SQL/学习记录/录音/密钥/教材）。

完成后仅报告 D02 结论、D01 关键回归、10D 整体验收条件与 10E 前置依赖，停止等待审核。
