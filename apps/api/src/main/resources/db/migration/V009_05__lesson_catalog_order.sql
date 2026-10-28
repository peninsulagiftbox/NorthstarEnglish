-- Nullable for existing standalone courses; never infer lesson identity or display numbers.
ALTER TABLE lesson
 ADD COLUMN sequence_no INT NULL,
 ADD COLUMN display_number VARCHAR(32) NULL,
 ADD CONSTRAINT ck_lesson_sequence CHECK (sequence_no IS NULL OR sequence_no > 0),
 ADD UNIQUE KEY uq_lesson_book_sequence (book_id, sequence_no);
