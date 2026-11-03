-- Ratings are append-only; (card_id, previous_row_version) is the database-level CAS guard.
CREATE TABLE concept_review_result (
  event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  card_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  rating VARCHAR(16) NOT NULL,
  origin VARCHAR(24) NOT NULL DEFAULT 'self_rating',
  scheduler_version VARCHAR(24) NOT NULL DEFAULT 'simple_v1',
  previous_due_at DATETIME(3) NOT NULL,
  next_due_at DATETIME(3) NOT NULL,
  previous_row_version BIGINT NOT NULL,
  client_occurred_at VARCHAR(40) NOT NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_concept_result_rating CHECK (rating IN ('again','good')),
  CONSTRAINT ck_concept_result_origin CHECK (origin='self_rating'),
  CONSTRAINT ck_concept_result_scheduler CHECK (scheduler_version='simple_v1'),
  UNIQUE KEY uq_concept_result_version(card_id,previous_row_version),
  FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
  FOREIGN KEY(card_id) REFERENCES concept_review_card(id)
);
-- Review history must survive only as written; no business path may rewrite or drop it.
DELIMITER //
CREATE TRIGGER concept_review_result_no_update BEFORE UPDATE ON concept_review_result FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Concept review results are immutable'; END//
CREATE TRIGGER concept_review_result_no_delete BEFORE DELETE ON concept_review_result FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Concept review results are immutable'; END//
DELIMITER ;
