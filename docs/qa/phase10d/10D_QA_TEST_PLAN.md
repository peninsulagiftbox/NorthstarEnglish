# Phase 10D-QA 测试计划（QA-PREP 交付）

日期：2026-10-31（Asia/Shanghai）。状态：QA-PREP 完成；QA-EXEC 未开始。
基线：QA worktree `test/10d-qa` @ `ff0dbe1f8b89a1817c2f5a0e7ba0755d5f971188`。
CORE 候选：未冻结。本计划对 CORE 未提交工作树（同 HEAD + 未提交变更）做了只读静态审计，被审计文件 SHA-256 见 `evidence/sha256-baseline.txt`。

## 0. 结论标记约定

- PASS：实际运行并通过，绑定候选 SHA 与退出码。
- FAIL：实际运行且复现缺陷。
- BLOCKED_BY_CORE：依赖 CORE 未冻结的 Schema/API/复习逻辑。
- NOT VERIFIED：本轮有计划与工具，但未实际运行。

D02（concept_review_card/source/result、CAS、自评分离、调度）在 CORE 工作树中完全不存在，全部 D02 条目为 BLOCKED_BY_CORE，不得写成 PASS。

## 1. D01 知识概念正确性（§四）

| ID | 层级 | 内容 | 状态 |
| --- | --- | --- | --- |
| D01-U01 | 设计检查 | canonicalKey 归一化规范（NFC、ASCII 空白折叠、trim、255 码点上限）与实现差异 | 静态审计完成（发现 QA-BUG-002） |
| D01-U02 | 单元/集成 | canonical_key 矩阵（fixtures/canonical_key_matrix.json，19 例）在隔离 MySQL 中逐例验证 Java 归一化与 utf8mb4_0900_bin 唯一性一致 | NOT VERIFIED（需 CORE 隔离库） |
| D01-U03 | 隔离DB | 同形异义（bank 金融/河岸）不合并；不同 senseKey 拒绝映射混用 | NOT VERIFIED（CORE 测试已声明覆盖，QA 独立复验） |
| D01-U04 | 隔离DB | 同义项跨课（look after）关联同一概念；保留 Lesson/Version/Sentence 身份 | NOT VERIFIED |
| D01-U05 | 隔离DB | 不同 kind 同名文本不合并；kind 错误关联被 CHECK/CLI 拒绝 | NOT VERIFIED |
| D01-U06 | 隔离DB | SQL 注入样本作为 canonicalKey 字面存储，不产生结构化影响 | NOT VERIFIED |
| D01-U07 | 静态 | lesson 级 occurrence 唯一键 NULL 失效（QA-BUG-001）的 DB 复现 | NOT VERIFIED（复现 SQL 已备） |
| D01-U08 | 静态 | 直接 SQL 写入绕过 Java 归一化（NBSP、尾随空格、大小写变体）产生的假性不合并边界 | NOT VERIFIED（写入账号限权前提下降级为 P3 观察） |

## 2. D01 跨课来源完整性（§五）

| ID | 层级 | 内容 | 状态 |
| --- | --- | --- | --- |
| D01-R01..R10 | 隔离DB+HTTP | 关系正例 10 项：概念多出现、句多出现、题多来源句、题多概念、attempt 冻结多来源、跨课同概念独立 attempt、双向钻取、多来源不被覆盖 | fixture/spec 已备（fixtures/concepts_course_a.json、concepts_course_b.json）；NOT VERIFIED |
| D01-N01..N14 | 隔离DB+HTTP | 关系负例 14 项：跨课引用、跨版本引用、不存在对象、重复登记、伪造 conceptId、同 eventId 重放/异 payload、撤回版本新建 attempt、NULL 绕过 CHECK | sql/negative_cases.sql 已备（N-01..N-17）；NOT VERIFIED |
| D01-N15 | 隔离DB | 每个负例后 DB 对账：无孤儿行、无非法写入（invariant_checks.sql I-01..I-08） | NOT VERIFIED |
| D01-I01 | 静态 | exercise_knowledge 对 lesson/paragraph 级 occurrence 缺少"题目源句落在该范围"校验（QA-BUG-007） | 静态审计完成 |

## 3. D01 学习证据不可变（§六）

| ID | 层级 | 内容 | 状态 |
| --- | --- | --- | --- |
| D01-IM01 | 隔离DB | 修改新版映射/发布新版本/撤回旧版/新增修订后：旧 attempt_knowledge source_json、source_sha256 byte-identical | NOT VERIFIED（CORE 报告已声明，QA 复验对账） |
| D01-IM02 | 隔离DB | 旧 correct、quiz_run 分母、learning_evidence、旧复习来源不变；不产生重复 receipt/event/attempt/evidence | NOT VERIFIED |
| D01-IM03 | 静态 | attempt_knowledge 无 UPDATE/DELETE 守卫（QA-BUG-003）；knowledge_concept_revision 可改（QA-BUG-004，含冻结后改解释不影响 relations_sha256） | 静态审计完成 |
| D01-IM04 | 隔离DB | 重放旧 eventId、同 eventId 异 payload、提交中断注入后全或无 | NOT VERIFIED |

## 4. D02 概念复习卡（§七）

D01 复习链（review_item/review_source/review_result/SimpleScheduler）在 CORE 工作树保持 10C-2 形态；concept_review_card/source/result、多来源聚合、CAS、幂等故障、自评分离（good 不生成 attempt/evidence、不出 correct、不进 Quiz 分母）全部未实现。**D02 全部条目 BLOCKED_BY_CORE**。测试矩阵（7.1 多来源、7.2 CAS 两连接并发、7.3 幂等故障注入、7.4 自评分离）已纳入本计划与 invariant_checks.sql，待契约冻结后执行。

## 5. 历史兼容（§八）

| ID | 内容 | 状态 |
| --- | --- | --- |
| D01-H01 | 旧 knowledge_point/favorite/reading_question/review_item/source/result/dueAt/reps/rowVersion 逐值不变 | NOT VERIFIED（对账 SQL 已备 I-05） |
| D01-H02 | 旧 simple_v1 调度、旧错题来源、旧 outbox 重试不变 | NOT VERIFIED |
| D01-H03 | 10C-2 动态题集与 verifiedRun 规则无回退（QuizScaleIntegrationTest、QuizReportR1IntegrationTest 复跑） | NOT VERIFIED |
| D01-H04 | 10C-1 共享音频与 Demo 独立音频可播放；旧历史可读 | NOT VERIFIED |

## 6. 权限与内容可见性（§九）

| ID | 内容 | 状态 |
| --- | --- | --- |
| D01-V01 | 不存在概念/越权 occurrence 404；撤回课程 occurrences 仅受限元数据 | NOT VERIFIED（CORE 已声明，QA 复验） |
| D01-V02 | lessonCount/firstOccurrenceId 聚合包含不可见课程（QA-BUG-005） | 静态审计完成 |
| D01-V03 | 多修订概念旧出现从浏览消失（QA-BUG-006） | 静态审计完成 |
| D01-V04 | cursor/limit/参数正则、SQL 注入、坏 Origin/Host 负例 | NOT VERIFIED |
| D01-V05 | attempt_knowledge.source_json 的接口暴露（D02 sources 端点）必须做内容权限 | BLOCKED_BY_CORE（当前无暴露面，无泄露通道） |

## 7. 迁移与恢复（§十）

| ID | 内容 | 状态 |
| --- | --- | --- |
| D01-M01 | 旧备份副本升级 + 空库全链初始化 + 重启快照一致 | BLOCKED_BY_CORE（等待冻结迁移 SHA；QA 复验 CORE 已声明结果） |
| D01-M02 | V012 各表 CHECK/FK/UQ 正反例（negative_cases.sql） | NOT VERIFIED |
| D01-M03 | DDL 部分提交、DML 回填失败、Flyway 登记失败演练 | BLOCKED_BY_CORE |
| D01-M04 | 新表进备份/导出恢复链（ExportController 分类、data-transfer 白名单） | 静态确认 CORE 已接入；端到端恢复 NOT VERIFIED |
| D01-M05 | 旧媒体 hash 不变、恢复后真实续学 | BLOCKED_BY_CORE |

## 8. QA-EXEC 执行顺序（冻结后）

1. 校验候选 SHA 与隔离库身份（容器/UUID/端口/schema 标签）。
2. 迁移正反例与 D01-U02/U07 规范化矩阵。
3. fixture A/B 登记 + D01-R/N 矩阵 + 每次 DB 前后对账。
4. 三路径提交（听写/阅读/quiz）证据冻结与不可变对账（D01-IM）。
5. D02 并发/幂等/自评分离（解除 BLOCKED 后）。
6. 浏览器 Playwright 流程 + 权限负例。
7. 备份恢复演练与历史兼容回归。
8. 汇总 EXECUTION/BUG/ACCEPTANCE 报告与脱敏包。
