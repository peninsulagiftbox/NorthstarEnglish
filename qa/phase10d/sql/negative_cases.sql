-- Phase 10D-QA SQL 负例与缺陷复现脚本（QA-PREP 版本）
-- 执行环境：CORE 冻结候选的隔离 MySQL（专用 schema，绝不对个人库执行）。
-- 每条 CASE 有 EXPECT 注释；EXEC 时记录 SQLSTATE/errno 与影响行数，并运行 invariant_checks.sql 对账。
-- 会话前设置唯一 QA 标记，便于误操作溯源：SET @qa_marker=(SELECT @@hostname);

-- ===== N-01 跨课 occurrence：A 版本登记时引用 B 课句子 =====
-- EXPECT: 1452 (FK sentence_id,version_id,paragraph_id 或服务层 422 KNOWLEDGE_CONTEXT_MISMATCH)
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-01','qa-con-bank-fin','qa-rev-bank-fin-1','qa-lesson-a','qa-ver-a1','sentence','qa-para-a1','qa-sb-011','{}');

-- ===== N-02 跨版本 exercise_knowledge：A 题关联 B 版 occurrence =====
-- EXPECT: 1452 (FK occurrence_id,version_id,concept_id) 或服务层 422
INSERT INTO exercise_knowledge(exercise_id,occurrence_id,version_id,concept_id,role)
VALUES ('qa-ex-read-multi','qa-occ-b-lookafter','qa-ver-a1','qa-con-lookafter','target');

-- ===== N-03 attempt_knowledge 引用其他 exercise 的 attempt =====
-- EXPECT: 1452 (FK attempt_id,exercise_id,version_id,sentence_id)
INSERT INTO attempt_knowledge(attempt_id,occurrence_id,exercise_id,version_id,concept_id,revision_id,sentence_id,role,source_json,source_sha256)
VALUES ('<other-exercise-attempt-uuid>','qa-occ-a-bank','qa-ex-read-multi','qa-ver-a1','qa-con-bank-fin','qa-rev-bank-fin-1','qa-sa-003','target','{}','0');

-- ===== N-04 CHECK NULL 绕过：sentence scope 且 paragraph_id NULL =====
-- EXPECT: 3819 (ck_occurrence_scope 已收紧：sentence scope 必须绑定 paragraph)；修复 QA-BUG-001 的一部分
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-04','qa-con-bank-fin','qa-rev-bank-fin-1','qa-lesson-a','qa-ver-a1','sentence',NULL,'qa-sa-003','{}');

-- ===== N-05 CHECK scope 非法组合：paragraph scope 带 sentence =====
-- EXPECT: 3819 (ck_occurrence_scope)
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-05','qa-con-bank-fin','qa-rev-bank-fin-1','qa-lesson-a','qa-ver-a1','paragraph','qa-para-a1','qa-sa-003','{}');

-- ===== N-06 同位置重复登记：同版本同修订同句再次插入 =====
-- EXPECT: 1062 (uq_occurrence_location)
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-06','qa-con-bank-fin','qa-rev-bank-fin-1','qa-lesson-a','qa-ver-a1','sentence','qa-para-a1','qa-sa-003','{}');

-- ===== N-07 缺陷复现 QA-BUG-001：lesson scope 重复登记（唯一键 NULL 失效） =====
-- EXPECT(已修复): 第二条插入 1062 (uq_occurrence_location 改用 location_guard 生成列)
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-07a','qa-con-so-that','qa-rev-sothat-1','qa-lesson-a','qa-ver-a1','lesson',NULL,NULL,'{}');
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa-occ-neg-07b','qa-con-so-that','qa-rev-sothat-1','qa-lesson-a','qa-ver-a1','lesson',NULL,NULL,'{}');

-- ===== N-08 同形异义合并不发生：bank 两义项同 canonicalKey 不同 senseKey 均可存在 =====
-- EXPECT: 两条 INSERT 均成功（证明不合并）
INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES ('qa-con-neg-08b','vocabulary','bank','bank.money_institution.qa2');

-- ===== N-09 同 kind+key+sense 重复概念 =====
-- EXPECT: 1062 (uq_concept_identity)
INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES ('qa-con-neg-09','vocabulary','bank','bank.money_institution.v1');

-- ===== N-10 非法 kind =====
-- EXPECT: 3819 (ck_knowledge_kind)
INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES ('qa-con-neg-10','phrase','so that','so_that.purpose.v1');

-- ===== N-11 冻结触发器：冻结后修改 occurrence =====
-- EXPECT: 45000 'Frozen knowledge relations are immutable'
UPDATE knowledge_occurrence SET usage_json='{"hacked":true}' WHERE id='qa-occ-a-bank';

-- ===== N-12 冻结触发器：冻结后插入 occurrence =====
-- EXPECT: 45000
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,usage_json)
VALUES ('qa-occ-neg-12','qa-con-bank-fin','qa-rev-bank-fin-1','qa-lesson-a','qa-ver-a1','lesson','{}');

-- ===== N-13 缺陷复现 QA-BUG-003：attempt_knowledge 快照可被 UPDATE/DELETE =====
-- EXPECT(已修复): 45000 attempt_knowledge_no_update
UPDATE attempt_knowledge SET source_json='{"tampered":true}' WHERE attempt_id='<real-attempt-uuid>' AND occurrence_id='qa-occ-a-bank';
-- EXPECT(已修复): 45000 attempt_knowledge_no_delete
DELETE FROM attempt_knowledge WHERE attempt_id='<real-attempt-uuid>' AND occurrence_id='qa-occ-a-bank';

-- ===== N-14 缺陷复现 QA-BUG-004：已确认修订可被改写（relations_sha256 不含解释） =====
-- EXPECT(已修复): 45000 knowledge_revision_no_update；relations_sha256 已纳入修订内容
UPDATE knowledge_concept_revision SET explanation='tampered' WHERE id='qa-rev-bank-fin-1';

-- ===== N-15 CHECK 修订确认一致性：confirmed 但 reviewed_at NULL =====
-- EXPECT: 3819 (ck_revision_confirmed)
INSERT INTO knowledge_concept_revision(id,concept_id,revision_no,display_name,explanation,source_ref,reviewer,review_status,reviewed_at)
VALUES ('qa-rev-neg-15','qa-con-bank-fin',2,'x','x','qa','qa','confirmed',NULL);

-- ===== N-16 伪造客户端 conceptId：正式提交 API body 携带 conceptId =====
-- EXPECT: HTTP 层忽略该参数；attempt_knowledge 只含 exercise_knowledge 冻结关系；对账 I-03

-- ===== N-17 缺陷复现 R-QA-011：occurrence 概念与修订分属不同概念（concept A 配 B 的修订） =====
-- 自包含夹具：不依赖 QA 种子课程；锚定已存在的 demo-01-v2（projection 未冻结时）。
INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES
  ('qa8n-con-a','vocabulary','qa8gate-neg','qa8n.a'),
  ('qa8n-con-b','vocabulary','qa8gate-neg','qa8n.b');
INSERT INTO knowledge_concept_revision(id,concept_id,revision_no,display_name,explanation,source_ref,reviewer,review_status,reviewed_at)
VALUES ('qa8n-rev-b','qa8n-con-b',1,'b','x','qa8n','automation-sources','confirmed',UTC_TIMESTAMP(3));
-- EXPECT(V012_08 起): 1452 (fk_occurrence_revision_concept)；修复前可插入（探针阶段已实证）
INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json)
VALUES ('qa8n-occ-cross','qa8n-con-a','qa8n-rev-b','demo-01','demo-01-v2','lesson',NULL,NULL,'{}');
SELECT COUNT(*) AS cross_inserted FROM knowledge_occurrence WHERE id='qa8n-occ-cross';
-- （由 HTTP 契约测试执行，非 SQL）

-- ===== N-17 撤回版本新建 attempt =====
-- EXPECT: HTTP 4xx 且无 exercise_attempt 行（对账 I-07）
-- （由 HTTP 契约测试执行，非 SQL）
