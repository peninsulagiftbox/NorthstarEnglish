# Phase 10D-QA 缺陷报告（第一轮：QA-PREP）

日期：2026-10-31。所有条目均为 **静态发现（STATIC）**，未实测复现；每条附最小复现步骤与复现脚本引用，QA-EXEC 时升级为已实测或撤销。候选版本：CORE 未提交工作树 @ ff0dbe1（文件 SHA-256 见 `evidence/sha256-baseline.txt`）。

## QA-BUG-001（P1，STATIC）

1. 影响：knowledge_occurrence lesson 级重复登记。
2. 等级：P1（错误概念关系可入库并被冻结投影永久封存；污染聚合统计与未来概念卡来源）。
3. 环境：CORE 候选 V012_02 + KnowledgeRegistrationCli。
4. 最小复现：对同一 versionId+revisionId 连续登记两条 lesson-scope occurrence（或同一登记文件重复条目）；预期报错/拒绝。
5. 预期：DB 拒绝（唯一键生效）或 CLI 422。
6. 实际（代码推定）：第二条 INSERT 成功——`uq_occurrence_location(version_id,revision_id,scope,paragraph_id,sentence_id)` 在 paragraph_id/sentence_id 均 NULL 时唯一键失效（MySQL 唯一索引多 NULL 允许），CLI 无 occurrence 去重查询，直接 INSERT。
7. DB 证据：复现脚本 `qa/phase10d/sql/negative_cases.sql` N-07；监控 `invariant_checks.sql` I-04。
8. 修复方向：唯一键改用生成列把 NULL 归一为哨兵值（如 `context_guard`），或 CLI 事务内按 (version,revision,scope,paragraph,sentence) 查重。
9. 阻断：阻断 D01-N07 负例验收；修复前不得 PASS。

## QA-BUG-002（P2，STATIC）

1. 影响：canonicalKey 未按设计折叠 Unicode 空白。
2. 等级：P2（方向为"假性不合并"，不会错误合并；违反 10D 计划 §3.1"Unicode空白首尾去除与连续空白折叠"条款）。
3. 复现：`KnowledgeConcepts.canonicalKey("look\u00A0after")` 返回含 NBSP 的键；`"\u00A0bank"` 首部 NBSP 不被 trim（Java `\s+` 与 trim 均只处理 ≤U+0020）。
4. 预期：NBSP 等合法 Unicode 空白折叠为 ASCII 空格（设计条款）或明确修订设计条款并更新验收。
5. 证据：`fixtures/canonical_key_matrix.json` 用例 nbsp_not_folded/nbsp_edge；实测定级待 EXEC。
6. 修复方向：`\\s+` 改为 UNICODE_CHARACTER_CLASS 或显式按 Character.isWhitespace 折叠。

## QA-BUG-003（P2，STATIC）

1. 影响：attempt_knowledge 快照在 SQL 层可 UPDATE/DELETE。
2. 等级：P2（runtime 正常路径不可达，但与 projection 表触发器防护标准不一致；表注释 "Frozen per-attempt knowledge sources" 名不副实）。
3. 复现：`UPDATE attempt_knowledge SET source_json=...` / `DELETE`（N-13）。
4. 修复方向：与 V012_06 同样的 no_update/no_delete 守卫触发器（或明确写入防护模型文档并降级）。
5. 阻断：D01-IM03 验收条目。

## QA-BUG-004（P2，STATIC）

1. 影响：已确认的概念修订可被 UPDATE/DELETE；且 `relations_sha256` 不含修订的 display_name/explanation，冻结后改写解释不会被投影哈希发现。
2. 等级：P2（历史 attempt 快照不受影响，但当前展示语义与冻结承诺可被静默篡改）。
3. 复现：N-14（UPDATE explanation 成功；relationsHash 复算不变）。
4. 修复方向：修订行 no_update/no_delete 守卫；解释修订走新 revision_no。

## QA-BUG-005（P2，STATIC）

1. 影响：`GET /knowledge/concepts` 的 lessonCount/firstOccurrenceId 在全部 occurrence 上聚合，未按可见性过滤；撤回/未发布课程的存在性通过聚合数字泄露。
2. 复现：登记跨课概念后将其中一课撤回，概念列表 lessonCount 不下降为可见课数（对照 I-08）。
3. 修复方向：COUNT DISTINCT 加可见性 CASE 过滤；firstOccurrenceId 取最小可见 occurrence。

## QA-BUG-006（P2，STATIC）

1. 影响：概念追加新的 confirmed 修订后，引用旧 confirmed 修订的 occurrence 从概念列表/详情消失（LATEST_REVISION JOIN 限定 `o.revision_id=最新修订`）。
2. 复现：为 qa-con-bank-fin 登记 revision_no=2 并确认，A/B 旧 occurrence 不再出现在详情 lessons 与列表计数。
3. 待决策：属设计取舍（occurrence 显式绑定选定修订）或缺陷；无论哪种，当前行为未在 CORE 报告/计划中声明，需 CORE 明确并在 D01-V03 验收。

## QA-BUG-007（P2，STATIC）

1. 影响：exercise_knowledge 登记时，lesson/paragraph 级 occurrence 未校验题目真实源句是否落在该范围（10D 计划 §3.3 要求）；仅 sentence 级有来源句包含校验。
2. 复现：把 A 课 P1 的 lesson-scope pattern 概念 occurrence 关联为 P2 句子的 exercise 的 target，登记成功。
3. 修复方向：CLI 校验 exercise_sentence 集合与 occurrence scope 的范围包含关系。

## 未决观察（无复现依据，不列缺陷）

- runtime 账号对 V012 新表的实际授权边界（R-QA-009）待 EXEC 用授权脚本核实。
- attempt 快照的接口暴露面（R-QA-010）随 D02 实现。

---

## 修复记录（2026-10-31 第二轮）

用户授权直接修复业务代码（覆盖 QA 隔离约束）。以下修复已应用于 CORE 工作树（未提交），Java 编译通过、新增单元测试 4/4 通过；数据库行为修复需 CORE 隔离库复跑集成测试后升级为已实测。

- QA-BUG-001：`V012_02` 新增 `location_guard` 生成列并将 `uq_occurrence_location` 改为 `(version_id,revision_id,location_guard)`；lesson/paragraph/sentence 三种 scope 各归一为单一可比较位置，lesson 级重复登记被 1062 拒绝。
- QA-BUG-002：`KnowledgeConcepts.canonicalKey` 按码点折叠全部合法 Unicode 空白（含 NBSP/U+2007/U+202F）为单 ASCII 空格并 trim；新增 `KnowledgeConceptsTest` 4 例。
- QA-BUG-003：`V012_07` 增加 `attempt_knowledge_no_update/no_delete` 触发器。
- QA-BUG-004：`V012_01` 增加 `knowledge_revision_no_update/no_delete` 触发器；`KnowledgeRegistrationCli.relationsHash` 纳入修订 `display_name/explanation/review_status`，冻结后改写解释将改变投影哈希。
- QA-BUG-005：`KnowledgeController.concepts()` 改为逐行可见性过滤聚合，`lessonCount/firstOccurrenceId` 只统计可见课程；全不可见概念不再返回。
- QA-BUG-006：概念列表与详情改为跨全部 confirmed 修订聚合 occurrence（显示名仍取最新 confirmed 修订），旧修订出现不再消失。
- QA-BUG-007 + R-QA-008：`KnowledgeRegistrationCli` 对 paragraph 级 occurrence 校验题目全部来源句落在同一段落；`ck_occurrence_scope` 收紧为 sentence scope 必须绑定 paragraph（复合 FK 从此始终生效）。
- 测试兼容：`KnowledgeSourcesIntegrationTest.TRIGGERS` 增补 4 个新触发器名，清理逻辑不受影响。

仍未解决（与修复无关）：R-QA-009（runtime 账号授权边界核查）、R-QA-010（D02 sources 端点内容权限）、D02 全部功能 = BLOCKED_BY_CORE。
