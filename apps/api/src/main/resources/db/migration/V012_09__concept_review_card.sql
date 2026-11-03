-- Cross-lesson concept cards; identity is the concept, never a lesson or sentence.
CREATE TABLE concept_review_card (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  owner_key VARCHAR(16) NOT NULL DEFAULT 'local',
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  prompt_kind VARCHAR(24) NOT NULL,
  protocol_version VARCHAR(24) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  due_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  reps INT NOT NULL DEFAULT 0,
  row_version BIGINT NOT NULL DEFAULT 1,
  scheduler_version VARCHAR(24) NOT NULL DEFAULT 'simple_v1',
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_concept_card_prompt CHECK (prompt_kind IN ('meaning_recall')),
  CONSTRAINT ck_concept_card_protocol CHECK (protocol_version IN ('concept_review_v1')),
  CONSTRAINT ck_concept_card_status CHECK (status IN ('pending')),
  CONSTRAINT ck_concept_card_scheduler CHECK (scheduler_version IN ('simple_v1')),
  CONSTRAINT ck_concept_card_reps CHECK (reps >= 0),
  UNIQUE KEY uq_concept_card(owner_key,concept_id,prompt_kind,protocol_version),
  UNIQUE KEY uq_concept_card_identity(id,concept_id),
  INDEX ix_concept_card_due(status,due_at,id),
  FOREIGN KEY(concept_id) REFERENCES knowledge_concept(id)
);
