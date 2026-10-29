-- MySQL CHECK accepts UNKNOWN: require an explicit non-NULL relation for confirmed targets.
-- Also make no-target edges unique; a nullable member of an ordinary UNIQUE key is insufficient.
ALTER TABLE version_sentence_map
 DROP CHECK ck_map_target,
 ADD CONSTRAINT ck_map_target_required CHECK(
   (mapping_status='confirmed' AND to_sentence_id IS NOT NULL AND relation IS NOT NULL AND relation IN ('equivalent','edited','split','merged'))
   OR (mapping_status='no_target' AND to_sentence_id IS NULL AND relation IS NULL)),
 ADD COLUMN target_uniqueness_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin
   GENERATED ALWAYS AS (COALESCE(to_sentence_id,'~no_target')) STORED,
 ADD UNIQUE KEY uq_mapping_target(from_version_id,to_version_id,from_sentence_id,target_uniqueness_key);
