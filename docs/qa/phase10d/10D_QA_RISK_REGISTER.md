# Phase 10D-QA 质量风险登记册

日期：2026-10-31。审计对象：CORE 未提交工作树（HEAD ff0dbe1 + 未提交 10D 实现），只读静态审计；文件 SHA-256 见 `evidence/sha256-baseline.txt`。静态发现与实测发现严格区分——本轮全部为 STATIC（未实测复现，复现脚本已备）。

## 风险矩阵

| ID | 等级 | 风险 | 现状/证据 | 缓解状态 |
| --- | --- | --- | --- | --- |
| R-QA-001 | P1 | lesson 级 occurrence 重复登记不受唯一键阻止（uq 含可空列，MySQL 多 NULL 允许），CLI 亦无去重检查；重复行会被冻结投影永久封存并污染 lessonCount/未来概念卡来源 | STATIC：V012_02 uq_occurrence_location + KnowledgeRegistrationCli 无 occurrence 去重查询 | 复现 SQL N-07、监控 I-04 已备；待 CORE 修复 |
| R-QA-002 | P2 | Unicode 空白（NBSP/U+2009 等）未按计划"Unicode 空白折叠"归一化（Java `\s+` 仅 ASCII），首尾 NBSP 不 trim；产生假性不同概念（安全方向为不合并） | STATIC：KnowledgeConcepts.canonicalKey | 矩阵用例 nbsp_* 已备；待实测定级 |
| R-QA-003 | P2 | attempt_knowledge 无 UPDATE/DELETE 守卫触发器；注释声称 "Frozen" 但 SQL 层可改/可删，与 projection 表防护不一致 | STATIC：V012_07 无触发器；V012_06 有守卫 | 复现 N-13 已备 |
| R-QA-004 | P2 | knowledge_concept_revision 行可 UPDATE/DELETE；冻结后改写确认解释不会改变 relations_sha256（hash 不含解释字段），展示语义可被静默篡改（历史 attempt 快照不受影响） | STATIC：V012_01 无守卫 + KnowledgeRegistrationCli.relationsHash 字段清单 | 复现 N-14 已备 |
| R-QA-005 | P2 | 概念列表 lessonCount/firstOccurrenceId 在所有 occurrence 上聚合，无逐行可见性过滤：撤回/未发布课程仍计入聚合，泄露撤回内容存在性 | STATIC：KnowledgeController.concepts SQL | 对照查询 I-08 已备 |
| R-QA-006 | P2 | 概念存在多个 confirmed 修订时，浏览仅 JOIN 最新修订，旧修订 occurrence 从列表/详情消失 | STATIC：LATEST_REVISION join `o.revision_id=r.id` | 待 CORE 决策（设计取舍 or 缺陷） |
| R-QA-007 | P2 | exercise_knowledge 对 lesson/paragraph 级 occurrence 未校验"题目真实源句落在该范围"（计划 10D §3.3 要求）；仅 sentence 级校验。审校错误可造成上下文错配的知识关联 | STATIC：KnowledgeRegistrationCli.exerciseKnowledge 循环 | 待 CORE 补校验或说明 |
| R-QA-008 | P3 | sentence-scope 且 paragraph NULL 时 CK 通过、复合 FK 跳过；CLI 会自动回填 paragraph，入口已挡，但直写 SQL 无 DB 层防线 | STATIC：V012_02 ck_occurrence_scope | N-04 记录边界 |
| R-QA-009 | P3 | 直接 SQL 写入绕过 Java 归一化（尾随空格/大小写变体可并存）；依赖写入账号限权（CLI 注释声称 runtime 账号无写权限，需 EXEC 核实授权脚本） | STATIC | EXEC 授权核查项 |
| R-QA-010 | 观察 | attempt 快照 source_json 含来源句全文；当前无接口暴露，D02 sources 端点实现时必须做内容权限，否则撤回课正文可能泄露 | STATIC：KnowledgeSources 快照内容 | BLOCKED_BY_CORE，纳入 D02 验收 |
| R-QA-011 | 观察 | revision 被改为非 confirmed 后，后续 attempt 的知识快照静默缺失（JOIN review_status='confirmed' 落空不报错） | STATIC：KnowledgeSources.record 查询 | 低概率；随 R-QA-004 一并修 |
| R-BLOCK-D02 | 阻塞 | D02 概念复习卡/CAS/幂等/自评分离完全未实现 | STATIC：无 concept_review_* 表与代码 | BLOCKED_BY_CORE |

## 与任务书风险清单的映射

任务书§三 16 项风险中：旧点误迁移（V012_03 双端复合 FK + CLI 同句校验，静态设计合理，待实测）、同形异义合并（sense_key 设计正确，待实测）、Unicode/唯一索引不一致（R-QA-002/009）、CHECK NULL 失效（R-QA-008/001）、跨版本引用（FK 设计正确，待实测 N-01/02）、attempt 来源覆盖（服务端快照设计正确，无 UPDATE 路径但 SQL 层可改 R-QA-003）、重复学习证据（receipt 幂等沿用，待实测）、多来源只留最后（当前无概念卡，BLOCKED）、CAS 丢更新（BLOCKED）、旧卡受新调度影响（旧链未动，待回归）、自评当客观（BLOCKED，D02 设计条款待验收）、撤回泄露（R-QA-005 + D01-V01 待实测）、新表备份链（静态已接入，端到端待验）、10C-2-R1 覆盖（worktree 基线含 R1 修复，待回归）。
