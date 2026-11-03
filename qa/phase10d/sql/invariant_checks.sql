-- Phase 10D-QA 数据完整性对账查询（QA-PREP 版本）
-- 在隔离库执行；每个查询带 EXPECT。任何一条出现 EXPECT 之外的结果即为缺陷证据。

-- I-01 无孤儿 attempt_knowledge（每行都能回链真实 attempt/题/出现）
-- EXPECT: count=0
SELECT COUNT(*) AS orphans FROM attempt_knowledge ak
LEFT JOIN exercise_attempt a ON a.id=ak.attempt_id AND a.exercise_id=ak.exercise_id AND a.version_id=ak.version_id AND a.sentence_id=ak.sentence_id
LEFT JOIN exercise_knowledge ek ON ek.exercise_id=ak.exercise_id AND ek.occurrence_id=ak.occurrence_id AND ek.version_id=ak.version_id AND ek.concept_id=ak.concept_id
WHERE a.id IS NULL OR ek.exercise_id IS NULL;

-- I-02 attempt_knowledge 与冻结 exercise_knowledge 的 role 一致
-- EXPECT: count=0
SELECT COUNT(*) AS role_mismatch FROM attempt_knowledge ak
JOIN exercise_knowledge ek ON ek.exercise_id=ak.exercise_id AND ek.occurrence_id=ak.occurrence_id AND ek.version_id=ak.version_id
WHERE ak.role<>ek.role;

-- I-03 attempt 不存在超出冻结关系的概念（伪造 conceptId 检测）
-- EXPECT: count=0
SELECT COUNT(*) AS extra_relations FROM attempt_knowledge ak
WHERE NOT EXISTS (SELECT 1 FROM exercise_knowledge ek WHERE ek.exercise_id=ak.exercise_id AND ek.occurrence_id=ak.occurrence_id AND ek.version_id=ak.version_id AND ek.concept_id=ak.concept_id);

-- I-04 lesson/paragraph scope 重复出现检测（QA-BUG-001 监控）
-- EXPECT: count=0（N-07 复现后应 >0，恢复后归零）
SELECT version_id,concept_id,revision_id,scope,COUNT(*) c FROM knowledge_occurrence
WHERE (scope='lesson' AND paragraph_id IS NULL AND sentence_id IS NULL) OR (scope='paragraph' AND sentence_id IS NULL)
GROUP BY version_id,concept_id,revision_id,scope HAVING c>1;

-- I-05 历史保护对账：旧表关键行数与 due/reps/row_version 摘要（EXEC 前后各取一次快照比对）
-- EXPECT: 前后快照逐值一致
SELECT (SELECT COUNT(*) FROM knowledge_point) kp,
       (SELECT COUNT(*) FROM vocabulary_favorite) fav,
       (SELECT COUNT(*) FROM review_item) ri,
       (SELECT COUNT(*) FROM review_source) rs,
       (SELECT COUNT(*) FROM review_result) rr,
       (SELECT COUNT(*) FROM quiz_run) qr,
       (SELECT COUNT(*) FROM learning_evidence) le,
       (SELECT COUNT(*) FROM command_receipt) cr;
SELECT id,due_at,reps,row_version FROM review_item ORDER BY id;

-- I-06 legacy 映射源探针（EXEC 时确定 demo knowledge_point id）

-- I-11 occurrence 修订与概念同属检测（R-QA-011 监控；V012_08 起由 fk_occurrence_revision_concept 兜底）
-- EXPECT: count=0
SELECT COUNT(*) AS cross_concept_occurrences FROM knowledge_occurrence o
LEFT JOIN knowledge_concept_revision r ON r.id=o.revision_id
WHERE r.id IS NULL OR r.concept_id<>o.concept_id;
SELECT kp.id,kp.lesson_id,kp.version_id,kp.sentence_id FROM knowledge_point kp JOIN lesson l ON l.id=kp.lesson_id WHERE l.id='demo-01' ORDER BY kp.id LIMIT 5;

-- I-07 撤回版本无新学习证据
-- EXPECT: count=0
SELECT COUNT(*) AS new_attempts_on_withdrawn FROM exercise_attempt a JOIN lesson_version v ON v.id=a.version_id WHERE v.publication_state='withdrawn' AND a.recorded_at > '<withdraw-execution-ts>';

-- I-08 概念可见性聚合：lessonCount 与逐课可见性独立复核（QA-BUG-005 对照）
-- EXPECT: 与 GET /knowledge/concepts 返回一致；撤回课不计入（现实现预计不一致）
SELECT c.id, COUNT(DISTINCT CASE WHEN l.availability='available' AND v.publication_state='published' AND (l.id='demo-01' OR lc.review_status='confirmed') THEN o.lesson_id END) AS visible_lessons,
       COUNT(DISTINCT o.lesson_id) AS all_lessons
FROM knowledge_concept c
JOIN knowledge_occurrence o ON o.concept_id=c.id
JOIN lesson_version v ON v.id=o.version_id JOIN lesson l ON l.id=o.lesson_id
JOIN content_license lc ON lc.id=v.license_id
GROUP BY c.id ORDER BY c.id;
