ALTER TABLE lesson_version
 ADD COLUMN publication_state VARCHAR(16) NOT NULL DEFAULT 'draft',
 ADD COLUMN content_readiness VARCHAR(24) NOT NULL DEFAULT 'basic_content',
 ADD COLUMN schema_version VARCHAR(64) NOT NULL DEFAULT 'northstar.local.basic.v1',
 ADD COLUMN published_at DATETIME(3) NULL,
 ADD CONSTRAINT ck_publication_state CHECK(publication_state IN ('draft','validated','published','withdrawn')),
 ADD CONSTRAINT ck_content_readiness CHECK(content_readiness IN ('legacy_unassessed','basic_content','teaching_complete'));
UPDATE lesson_version SET publication_state='published',content_readiness='legacy_unassessed',schema_version='northstar.legacy.demo.v1'
 WHERE lesson_id='demo-01' AND id IN ('demo-01-v1','demo-01-v2');
