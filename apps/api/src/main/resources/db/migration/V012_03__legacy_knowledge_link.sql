-- Legacy knowledge_point rows keep their original identity; links only record reviewed mappings.
CREATE TABLE legacy_knowledge_link (
  knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  occurrence_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  mapping_basis VARCHAR(48) NOT NULL,
  reviewer VARCHAR(128) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_legacy_basis CHECK (mapping_basis IN ('manual_review','synthetic_fixture_reviewed')),
  PRIMARY KEY(knowledge_point_id),
  UNIQUE KEY uq_legacy_context(knowledge_point_id,version_id,sentence_id),
  UNIQUE KEY uq_legacy_occurrence(occurrence_id),
  FOREIGN KEY(knowledge_point_id,version_id,sentence_id) REFERENCES knowledge_point(id,version_id,sentence_id),
  FOREIGN KEY(occurrence_id) REFERENCES knowledge_occurrence(id),
  FOREIGN KEY(concept_id) REFERENCES knowledge_concept(id)
);
