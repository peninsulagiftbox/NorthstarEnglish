-- Resolve the actual legacy CHECK by expression, never assume an auto-generated name.
SET @start_check = (SELECT MIN(constraint_name) FROM information_schema.check_constraints
 WHERE constraint_schema=DATABASE() AND REPLACE(REPLACE(REPLACE(check_clause,'`',''),' ',''),'(', '') IN ('start_ms=0)','start_ms=0'));
SET @start_sql = IF(@start_check IS NULL,'SELECT * FROM northstar_missing_legacy_start_constraint',
 CONCAT('ALTER TABLE sentence DROP CHECK `',REPLACE(@start_check,'`','``'),'`, ADD CONSTRAINT ck_sentence_start CHECK (start_ms >= 0)'));
PREPARE northstar_start FROM @start_sql;
EXECUTE northstar_start;
DEALLOCATE PREPARE northstar_start;
