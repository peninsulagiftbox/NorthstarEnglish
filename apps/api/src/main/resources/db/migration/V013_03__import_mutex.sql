CREATE TABLE import_mutex (
 id VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 CONSTRAINT ck_import_mutex CHECK(id='content-import')
);
