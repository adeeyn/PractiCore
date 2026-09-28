-- Optional per-student profile photo. The value is the path relative to static/
-- (e.g. uploads/avatars/7_ab12cd34.png); NULL means "use the default avatar".

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS avatar_path VARCHAR(255) NULL AFTER course;

-- Older rows used 'default.png' as a sentinel meaning "no photo". Real uploads always
-- live under uploads/, so the sentinel is normalised to NULL (safe to run repeatedly).
UPDATE students
SET avatar_path = NULL
WHERE avatar_path IN ('', 'default.png');

-- The old column default wrote that same sentinel on every new row, so drop it
ALTER TABLE students
    MODIFY avatar_path VARCHAR(255) NULL DEFAULT NULL;
