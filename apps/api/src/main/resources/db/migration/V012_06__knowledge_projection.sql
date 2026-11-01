-- Freezing the projection keeps registered relations immutable while attempts may still be recorded.
CREATE TABLE knowledge_projection (
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  protocol_version VARCHAR(32) NOT NULL,
  relations_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  registered_by VARCHAR(128) NOT NULL,
  frozen BOOLEAN NOT NULL DEFAULT FALSE,
  frozen_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_projection_frozen CHECK (frozen=FALSE OR frozen_at IS NOT NULL),
  FOREIGN KEY(version_id) REFERENCES lesson_version(id)
);
DELIMITER //
CREATE TRIGGER knowledge_projection_no_insert BEFORE INSERT ON knowledge_projection FOR EACH ROW
BEGIN
 IF NEW.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Projection freezes only after relations are registered'; END IF;
END//
CREATE TRIGGER knowledge_projection_no_update BEFORE UPDATE ON knowledge_projection FOR EACH ROW
BEGIN
 IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge projection is immutable'; END IF;
END//
CREATE TRIGGER knowledge_projection_no_delete BEFORE DELETE ON knowledge_projection FOR EACH ROW
BEGIN
 IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge projection is immutable'; END IF;
END//
CREATE TRIGGER occurrence_no_insert BEFORE INSERT ON knowledge_occurrence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER occurrence_no_update BEFORE UPDATE ON knowledge_occurrence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER occurrence_no_delete BEFORE DELETE ON knowledge_occurrence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER legacy_link_no_insert BEFORE INSERT ON legacy_knowledge_link FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER legacy_link_no_update BEFORE UPDATE ON legacy_knowledge_link FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER legacy_link_no_delete BEFORE DELETE ON legacy_knowledge_link FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_sentence_no_insert BEFORE INSERT ON exercise_sentence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_sentence_no_update BEFORE UPDATE ON exercise_sentence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_sentence_no_delete BEFORE DELETE ON exercise_sentence FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_knowledge_no_insert BEFORE INSERT ON exercise_knowledge FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_knowledge_no_update BEFORE UPDATE ON exercise_knowledge FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
CREATE TRIGGER exercise_knowledge_no_delete BEFORE DELETE ON exercise_knowledge FOR EACH ROW
BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge relations are immutable'; END IF; END//
DELIMITER ;
