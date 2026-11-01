-- Global concepts are separate from per-sentence knowledge_point rows; sense_key prevents merging homonyms.
CREATE TABLE knowledge_concept (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  kind VARCHAR(24) NOT NULL,
  canonical_key VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,
  sense_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_knowledge_kind CHECK (kind IN ('vocabulary','grammar','collocation','pattern')),
  UNIQUE KEY uq_concept_identity(kind,canonical_key,sense_key)
);
CREATE TABLE knowledge_concept_revision (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  revision_no INT NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  explanation TEXT NOT NULL,
  source_ref VARCHAR(255) NOT NULL,
  reviewer VARCHAR(128) NOT NULL,
  review_status VARCHAR(24) NOT NULL,
  reviewed_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_revision_no CHECK (revision_no >= 1),
  CONSTRAINT ck_revision_status CHECK (review_status IN ('pending_review','confirmed','rejected')),
  CONSTRAINT ck_revision_confirmed CHECK ((review_status='confirmed') = (reviewed_at IS NOT NULL)),
  UNIQUE KEY uq_concept_revision(concept_id,revision_no),
  FOREIGN KEY(concept_id) REFERENCES knowledge_concept(id)
);
-- Revisions are append-only; displayed semantics can only change through a new reviewed revision.
DELIMITER //
CREATE TRIGGER knowledge_revision_no_update BEFORE UPDATE ON knowledge_concept_revision FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Knowledge concept revisions are append-only'; END//
CREATE TRIGGER knowledge_revision_no_delete BEFORE DELETE ON knowledge_concept_revision FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Knowledge concept revisions are append-only'; END//
DELIMITER ;
