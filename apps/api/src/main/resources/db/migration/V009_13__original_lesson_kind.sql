ALTER TABLE lesson DROP CHECK lesson_chk_1, ADD CONSTRAINT ck_lesson_kind CHECK(kind IN ('original_demo','original','licensed'));
