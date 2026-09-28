-- The CP2 write-up says the NLP step extracts education, certifications,
-- experience and projects alongside skills. ResumeParser now returns those
-- sections, so they get their own columns instead of being dropped.
-- Safe to run more than once (MariaDB IF NOT EXISTS syntax).

ALTER TABLE student_resumes
    ADD COLUMN IF NOT EXISTS education       TEXT NULL AFTER file_size,
    ADD COLUMN IF NOT EXISTS certifications  TEXT NULL AFTER education,
    ADD COLUMN IF NOT EXISTS experience      TEXT NULL AFTER certifications,
    ADD COLUMN IF NOT EXISTS projects        TEXT NULL AFTER experience;
