DELIMITER //
CREATE TRIGGER quiz_set_no_update BEFORE UPDATE ON exercise_set FOR EACH ROW
BEGIN
 IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz set is immutable'; END IF;
 IF NEW.frozen AND ((SELECT COUNT(*) FROM exercise_set_item WHERE set_id=OLD.id) NOT BETWEEN 1 AND 100 OR (SELECT MAX(ordinal) FROM exercise_set_item WHERE set_id=OLD.id)<>(SELECT COUNT(*) FROM exercise_set_item WHERE set_id=OLD.id)) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cannot freeze empty or unordered quiz set'; END IF;
END//
CREATE TRIGGER quiz_set_no_delete BEFORE DELETE ON exercise_set FOR EACH ROW
BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz set is immutable'; END IF; END//
CREATE TRIGGER quiz_item_no_insert BEFORE INSERT ON exercise_set_item FOR EACH ROW
BEGIN IF (SELECT frozen FROM exercise_set WHERE id=NEW.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END//
CREATE TRIGGER quiz_item_no_update BEFORE UPDATE ON exercise_set_item FOR EACH ROW
BEGIN IF (SELECT frozen FROM exercise_set WHERE id=OLD.set_id) OR (SELECT frozen FROM exercise_set WHERE id=NEW.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END//
CREATE TRIGGER quiz_item_no_delete BEFORE DELETE ON exercise_set_item FOR EACH ROW
BEGIN IF (SELECT frozen FROM exercise_set WHERE id=OLD.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END//
DELIMITER ;
