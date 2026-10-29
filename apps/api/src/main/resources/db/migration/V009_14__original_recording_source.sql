ALTER TABLE audio_asset DROP CHECK audio_asset_chk_1, ADD CONSTRAINT ck_audio_source_kind CHECK(source_kind IN ('original_tts','original_recording','licensed_audio'));
