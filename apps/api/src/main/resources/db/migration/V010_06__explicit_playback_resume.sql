-- No backfill: existing position_ms and all old columns retain their exact values.
ALTER TABLE study_resume
 ADD COLUMN playback_coordinate VARCHAR(24) NULL CHECK (playback_coordinate IS NULL OR playback_coordinate='segment_offset_v1'),
 ADD COLUMN playback_mode VARCHAR(16) NULL CHECK (playback_mode IS NULL OR playback_mode IN ('segment','full')),
 ADD COLUMN full_asset_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD COLUMN asset_position_ms INT NULL,
 ADD CONSTRAINT fk_resume_full_audio FOREIGN KEY (full_asset_id,version_id) REFERENCES lesson_audio(asset_id,version_id),
 ADD CONSTRAINT ck_resume_full_position CHECK (
  (COALESCE(playback_mode,'segment')='segment' AND full_asset_id IS NULL AND asset_position_ms IS NULL)
  OR (playback_mode='full' AND full_asset_id IS NOT NULL AND asset_position_ms IS NOT NULL AND asset_position_ms>=0));
