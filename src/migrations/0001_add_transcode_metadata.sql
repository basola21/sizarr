-- depends:

ALTER TABLE transcoded ADD COLUMN size_before INTEGER;
ALTER TABLE transcoded ADD COLUMN size_after INTEGER;
ALTER TABLE transcoded ADD COLUMN codec_before TEXT;
ALTER TABLE transcoded ADD COLUMN duration_seconds REAL;
