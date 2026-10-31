-- Guard is repeated in the same transaction as the additive backfill.
SET SESSION group_concat_max_len=65535;
START TRANSACTION;
SET @bad_quiz = (
 SELECT COUNT(*) FROM quiz_run r LEFT JOIN lesson_version v ON v.id=r.version_id LEFT JOIN command_receipt c ON c.event_id=r.event_id
 WHERE v.lesson_id<>r.lesson_id OR c.response_json IS NULL
 OR JSON_UNQUOTE(JSON_EXTRACT(c.response_json,'$.runId'))<>r.id
 OR CAST(JSON_EXTRACT(c.response_json,'$.correctCount') AS UNSIGNED)<>r.correct_count
 OR (SELECT COUNT(*) FROM quiz_answer b WHERE b.run_id=r.id)<>3
 OR (SELECT COUNT(*) FROM quiz_question q WHERE q.version_id=r.version_id)<>3
 OR r.correct_count<>(SELECT COALESCE(SUM(a.correct),0) FROM quiz_answer b JOIN exercise_attempt a ON a.id=b.attempt_id WHERE b.run_id=r.id)
);
SET @bad_quiz = @bad_quiz + (
 SELECT COUNT(*) FROM quiz_answer b JOIN quiz_run r ON r.id=b.run_id
 LEFT JOIN exercise_attempt a ON a.id=b.attempt_id
 LEFT JOIN quiz_question q ON q.exercise_id=b.exercise_id
 LEFT JOIN command_receipt c ON c.event_id=a.event_id
 WHERE a.id IS NULL OR q.exercise_id IS NULL OR c.response_json IS NULL
 OR NOT (b.version_id=r.version_id AND a.version_id=b.version_id AND q.version_id=b.version_id AND a.lesson_id=r.lesson_id AND a.sentence_id=b.sentence_id AND q.sentence_id=b.sentence_id AND a.exercise_id=b.exercise_id)
 OR (SELECT COUNT(*) FROM learning_evidence e WHERE e.attempt_id=a.id AND e.event_id=a.event_id)<>1
 OR JSON_UNQUOTE(JSON_EXTRACT(a.result_json,'$.answerKey'))<>JSON_UNQUOTE(JSON_EXTRACT(q.payload_json,'$.answerKey'))
 OR a.correct<>(b.option_id=JSON_UNQUOTE(JSON_EXTRACT(q.payload_json,'$.answerKey')))
 OR JSON_UNQUOTE(JSON_EXTRACT(a.result_json,'$.optionId'))<>b.option_id
 OR NOT JSON_CONTAINS(JSON_EXTRACT(q.payload_json,'$.options'),JSON_OBJECT('id',b.option_id))
 OR c.payload_hash<>SHA2(CONCAT(r.event_id,':',b.exercise_id),256)
 OR c.response_json<>a.result_json
);
SET @guard = IF(@bad_quiz=0,'SELECT 1','SELECT * FROM northstar_invalid_quiz_history_STOP');
PREPARE quiz_guard FROM @guard;
EXECUTE quiz_guard;
DEALLOCATE PREPARE quiz_guard;
INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin)
 SELECT UUID(),version_id,'practice','quiz_choice_v1','legacy_reconstructed' FROM quiz_question GROUP BY version_id;
INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash)
 SELECT id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,payload_json,
 SHA2(CONCAT(HEX(exercise_id),':',ordinal,':',HEX(sentence_id),':',HEX(knowledge_point_id),':',HEX(CAST(payload_json AS CHAR CHARACTER SET utf8mb4))),256)
 FROM (SELECT s.id,q.*,ROW_NUMBER() OVER(PARTITION BY q.version_id ORDER BY q.exercise_id) ordinal FROM quiz_question q JOIN exercise_set s ON s.version_id=q.version_id) ordered;
UPDATE exercise_set s JOIN (
 SELECT set_id,GROUP_CONCAT(item_hash ORDER BY ordinal SEPARATOR '') hashes FROM exercise_set_item GROUP BY set_id
) items ON items.set_id=s.id
 SET s.set_hash=SHA2(CONCAT('quiz-set-v1:',HEX(s.version_id),':practice:quiz_choice_v1:',COALESCE(HEX(s.context_group_id),''),':',items.hashes),256),s.frozen=TRUE;
UPDATE quiz_run r JOIN exercise_set s ON s.version_id=r.version_id
 JOIN (SELECT run_id,COUNT(*) n FROM quiz_answer GROUP BY run_id) answers ON answers.run_id=r.id
 SET r.total_count=answers.n,r.submitted_count=answers.n,r.set_id=s.id,r.set_hash=s.set_hash,r.exposure_status='unknown',r.measurement_policy_version='quiz_choice_v1';
INSERT INTO quiz_run_item(run_id,exercise_id,version_id,sentence_id,set_id,set_hash,ordinal,question_json,attempt_id,option_id)
 SELECT b.run_id,b.exercise_id,b.version_id,b.sentence_id,r.set_id,r.set_hash,i.ordinal,i.question_json,b.attempt_id,b.option_id
 FROM quiz_answer b JOIN quiz_run r ON r.id=b.run_id JOIN exercise_set_item i ON i.set_id=r.set_id AND i.exercise_id=b.exercise_id;
COMMIT;
