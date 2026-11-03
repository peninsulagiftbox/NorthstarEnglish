-- An occurrence revision must belong to the occurrence's concept; the single-column revision FK alone allowed cross-concept pairs.
ALTER TABLE knowledge_concept_revision
  ADD UNIQUE KEY uq_revision_id_concept(id, concept_id);
ALTER TABLE knowledge_occurrence
  ADD CONSTRAINT fk_occurrence_revision_concept
    FOREIGN KEY(revision_id, concept_id) REFERENCES knowledge_concept_revision(id, concept_id);
