-- Derived dialogue grouping; frozen lesson payloads and all pre-existing columns remain untouched.
-- Preconditions in the rehearsal harness require exactly the two reviewed Demo versions and 20 sentences.
START TRANSACTION;
INSERT INTO paragraph(id,version_id,stable_key,sequence_no)
 SELECT 'af61b21b-371a-4550-85a2-8301db66a325',id,'original-dialogue',1
 FROM lesson_version WHERE id='demo-01-v1' AND lesson_id='demo-01';
INSERT INTO paragraph(id,version_id,stable_key,sequence_no)
 SELECT 'a214bafb-e722-4f77-b5ed-62311f41b116',id,'original-dialogue',1
 FROM lesson_version WHERE id='demo-01-v2' AND lesson_id='demo-01';
UPDATE sentence SET paragraph_id=CASE lesson_version_id
 WHEN 'demo-01-v1' THEN 'af61b21b-371a-4550-85a2-8301db66a325'
 WHEN 'demo-01-v2' THEN 'a214bafb-e722-4f77-b5ed-62311f41b116'
 END WHERE lesson_id='demo-01' AND lesson_version_id IN ('demo-01-v1','demo-01-v2');
COMMIT;
