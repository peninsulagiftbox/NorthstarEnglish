ALTER TABLE sentence
 MODIFY COLUMN paragraph_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD KEY ix_sentence_paragraph_version(paragraph_id,lesson_version_id),
 ADD CONSTRAINT fk_sentence_paragraph_version FOREIGN KEY(paragraph_id,lesson_version_id)
 REFERENCES paragraph(id,version_id);
