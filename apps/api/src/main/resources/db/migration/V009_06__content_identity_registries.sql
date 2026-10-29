CREATE TABLE sentence_identity (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY, lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, registry_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 UNIQUE KEY uq_sentence_identity_registry(lesson_id,registry_key),
 UNIQUE KEY uq_sentence_identity_lesson(id,lesson_id),
 FOREIGN KEY(lesson_id) REFERENCES lesson(id)
);
CREATE TABLE paragraph_identity (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY, lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, registry_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 UNIQUE KEY uq_paragraph_identity_registry(lesson_id,registry_key),
 UNIQUE KEY uq_paragraph_identity_lesson(id,lesson_id),
 FOREIGN KEY(lesson_id) REFERENCES lesson(id)
);
