# Phase 10D-QA 原创测试 Fixture 规范

日期：2026-10-31。所有文本为本 QA 会话原创撰写，不含教材原文；音频不需要。Fixture 语义字段格式与 CORE `KnowledgeRegistrationCli` 实际入参一致（只读审计得出，见 qa/phase10d/fixtures/*.json）。

## 1. 课程结构（待 QA-EXEC 隔离库播种）

| 对象 | ID | 说明 |
| --- | --- | --- |
| Lesson A | `qa-lesson-a` | "Community Garden Workshop"，original，license confirmed |
| Version A1 | `qa-ver-a1` | published；2 段落 12 句（P1: qa-sa-001..006，P2: qa-sa-007..012） |
| Version A0 | `qa-ver-a0` | withdrawn 同内容旧版（可见性负例用），含 qa-sa-001 的 A0 副本 |
| Lesson B | `qa-lesson-b` | "Riverside Notebook"，original，license confirmed |
| Version B1 | `qa-ver-b1` | published；3 段落 24 句（qa-sb-001..024） |
| Exercise | `qa-ex-read-multi`(A1 多来源阅读)、`qa-ex-quiz-multi`(B1 多目标 quiz)、`qa-ex-dict-1`(A1 听写) | kind 与种子脚本一致 |
| Legacy 映射源 | demo-01 现存一个 knowledge_point（QA-EXEC 时用 I-06 查询确定 id 后写入 legacyLinks） | 不改旧表 |

句子文本由 QA-EXEC 播种脚本写入；本规范与 JSON fixture 定义登记关系，播种 SQL 属 QA-EXEC 范围（依赖冻结 schema，见 TEST_PLAN §8）。

## 2. 概念清单

| Concept ID | kind | canonicalKey | senseKey | 出现 |
| --- | --- | --- | --- | --- |
| qa-con-bank-fin | vocabulary | bank | bank.money_institution.v1 | A1 sentence-scope qa-sa-003 |
| qa-con-bank-riv | vocabulary | bank | bank.river_edge.v1 | B1 sentence-scope qa-sb-011 |
| qa-con-lookafter | collocation | look after | look_after.care_for.v1 | A1 qa-sa-005 与 B1 qa-sb-004（跨课同义项） |
| qa-con-pres-passive | grammar | present passive | present_passive.v1 | A1 qa-sa-008、B1 qa-sb-017 |
| qa-con-so-that | pattern | so that | so_that.purpose.v1 | A1 lesson-scope |
| qa-con-takeup | vocabulary | take up | take_up.start_hobby.v1 | B1 qa-sb-020 |

验收点：bank 两义项同 canonicalKey 不同 senseKey 不合并；look after 跨课同义项聚合；grammar/pattern 与 vocabulary 同名不跨类合并。

## 3. 登记文件

- `fixtures/concepts_course_a.json`：reviewer=`qa-fixture-reviewer`；A1 的概念修订、5 个 occurrence（含 lesson-scope so that）、exerciseSentences/exerciseKnowledge。relations>0 → CLI 冻结投影。
- `fixtures/concepts_course_b.json`：B1 同构；含 bank-riv、跨课 look-after、take-up。
- `fixtures/canonical_key_matrix.json`：19 个规范化用例（期望键/期望错误），供 D01-U02 驱动。

## 4. 多来源/多目标关系（§5.1 正例锚点）

1. `qa-ex-read-multi`：exercise_sentence = qa-sa-003(primary)+qa-sa-008(supporting)；exercise_knowledge = bank-fin(target)+pres-passive(support)。
2. `qa-ex-quiz-multi`：exercise_sentence = qa-sb-004(primary)+qa-sb-020(supporting)；exercise_knowledge = look-after(target)+take-up(target)。
3. A/B 各产生一次错误 attempt（QA-EXEC 经正式 API），验证跨课同概念聚合为一张（未来的）概念卡且两条来源独立保留。

## 5. 负例数据（sql/negative_cases.sql）

N-01..N-17 覆盖：跨课/跨版本 occurrence/exercise/attempt 引用、不存在对象、CHECK NULL 绕过（sentence scope 无 paragraph、lesson scope 重复登记）、重复 PK/UQ、冻结触发器、非法 role/scope、attempt_knowledge 直改直删（缺陷复现 QA-BUG-003/004）。每条含 EXPECT 注释；EXEC 时逐条比对 SQLSTATE/错误码并跑 invariant_checks.sql 确认零副作用。

## 6. 禁止事项

- 不使用四册或任何受版权保护文本；全部句子为本规范作者原创。
- 不修改 CORE 的 V012 迁移、Controller、正式页面；播种与负例只写隔离库。
- 不对个人学习库（3308）执行任何写入或故障注入。
