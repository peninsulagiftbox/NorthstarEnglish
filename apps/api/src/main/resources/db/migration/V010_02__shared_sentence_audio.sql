-- This DDL commits independently. V010.01 must already provide the FK support index.
ALTER TABLE sentence DROP INDEX uq_sentence_audio;
