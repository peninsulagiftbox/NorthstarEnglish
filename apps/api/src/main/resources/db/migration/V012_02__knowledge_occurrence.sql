-- Composite key lets occurrence references verify the sentence/paragraph belongs to the same version.
ALTER TABLE sentence
 ADD UNIQUE KEY uq_sentence_paragraph(id,lesson_version_id,paragraph_id);
CREATE TABLE knowledge_occurrence (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  revision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  scope VARCHAR(16) NOT NULL,
  paragraph_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  -- NULL-bearing unique keys never dedupe in MySQL; the guard collapses each scope to one comparable location.
  location_guard VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin
    GENERATED ALWAYS AS (CASE scope WHEN 'lesson' THEN 'L' WHEN 'paragraph' THEN CONCAT('P:',paragraph_id) ELSE CONCAT('S:',sentence_id) END) STORED,
  usage_json JSON NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_occurrence_scope CHECK (
    (scope='lesson' AND paragraph_id IS NULL AND sentence_id IS NULL)
    OR (scope='paragraph' AND paragraph_id IS NOT NULL AND sentence_id IS NULL)
    OR (scope='sentence' AND paragraph_id IS NOT NULL AND sentence_id IS NOT NULL)),
  UNIQUE KEY uq_occurrence_context(id,version_id,concept_id),
  UNIQUE KEY uq_occurrence_location(version_id,revision_id,location_guard),
  FOREIGN KEY(concept_id) REFERENCES knowledge_concept(id),
  FOREIGN KEY(revision_id) REFERENCES knowledge_concept_revision(id),
  FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
  FOREIGN KEY(paragraph_id,version_id) REFERENCES paragraph(id,version_id),
  FOREIGN KEY(sentence_id,version_id,paragraph_id) REFERENCES sentence(id,lesson_version_id,paragraph_id)
);
