-- Keep a nonunique index supporting the existing same-version FK before removing uniqueness.
SET @audio_index_ok = (SELECT COUNT(*) FROM (SELECT index_name FROM information_schema.statistics
 WHERE table_schema=DATABASE() AND table_name='sentence' AND non_unique=1
 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index)='audio_asset_id,lesson_version_id') AS supporting);
SET @audio_index_sql = IF(@audio_index_ok>0,'SELECT 1',
 'ALTER TABLE sentence ADD INDEX ix_sentence_asset_version (audio_asset_id,lesson_version_id)');
PREPARE northstar_audio_index FROM @audio_index_sql;
EXECUTE northstar_audio_index;
DEALLOCATE PREPARE northstar_audio_index;
