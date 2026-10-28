-- The new column is the only old-table extension allowed by this candidate.
ALTER TABLE sentence ADD COLUMN paragraph_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL;
