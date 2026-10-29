ALTER TABLE sentence
 MODIFY identity_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD UNIQUE KEY uq_sentence_identity(lesson_version_id,identity_id),
 ADD UNIQUE KEY uq_sentence_context(id,lesson_version_id,lesson_id),
 ADD CONSTRAINT fk_sentence_identity FOREIGN KEY(identity_id,lesson_id) REFERENCES sentence_identity(id,lesson_id);
ALTER TABLE paragraph
 MODIFY lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, MODIFY identity_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD UNIQUE KEY uq_paragraph_identity(version_id,identity_id),
 ADD CONSTRAINT fk_paragraph_lesson FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
 ADD CONSTRAINT fk_paragraph_identity FOREIGN KEY(identity_id,lesson_id) REFERENCES paragraph_identity(id,lesson_id);
