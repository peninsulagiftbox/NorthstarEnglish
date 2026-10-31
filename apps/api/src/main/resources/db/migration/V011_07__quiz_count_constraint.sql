SET @correct_check=(SELECT MIN(c.constraint_name) FROM information_schema.check_constraints c JOIN information_schema.table_constraints t USING(constraint_schema,constraint_name) WHERE c.constraint_schema=DATABASE() AND t.table_name='quiz_run' AND c.check_clause LIKE '%correct_count%' AND c.check_clause LIKE '%3%');
SET @correct_sql=IF(@correct_check IS NULL,'SELECT * FROM northstar_missing_legacy_quiz_check',CONCAT('ALTER TABLE quiz_run DROP CHECK `',REPLACE(@correct_check,'`','``'),'`, ADD CONSTRAINT ck_quiz_counts CHECK (total_count BETWEEN 1 AND 100 AND submitted_count=total_count AND correct_count BETWEEN 0 AND submitted_count)'));
PREPARE quiz_counts FROM @correct_sql;
EXECUTE quiz_counts;
DEALLOCATE PREPARE quiz_counts;
