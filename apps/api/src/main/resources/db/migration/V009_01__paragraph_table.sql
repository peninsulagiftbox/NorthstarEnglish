-- Isolated rehearsal candidate only; never place in the personal application's migration location.
CREATE TABLE paragraph (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 stable_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sequence_no INT NOT NULL,
 UNIQUE KEY uq_paragraph_version(id,version_id),
 UNIQUE KEY uq_paragraph_key(version_id,stable_key),
 UNIQUE KEY uq_paragraph_sequence(version_id,sequence_no),
 CONSTRAINT ck_paragraph_sequence CHECK(sequence_no > 0),
 CONSTRAINT fk_paragraph_version FOREIGN KEY(version_id) REFERENCES lesson_version(id)
);
