ALTER TABLE quiz_question ADD UNIQUE KEY uq_question_context(exercise_id,version_id,sentence_id,knowledge_point_id);
ALTER TABLE exercise_attempt ADD UNIQUE KEY uq_attempt_exercise(id,exercise_id,version_id,sentence_id);
ALTER TABLE quiz_answer ADD UNIQUE KEY uq_answer_attempt(run_id,exercise_id,attempt_id,version_id,sentence_id,option_id);
