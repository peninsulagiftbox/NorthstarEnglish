-- Quiz review history is append-only; ratings must never be rewritten.
DELIMITER //
CREATE TRIGGER review_result_no_update BEFORE UPDATE ON review_result FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Quiz review results are immutable'; END//
DELIMITER ;
