-- Optional per-company logo image, uploaded from the employer Company Profile page.
-- The value is the path relative to static/ (e.g. uploads/logos/3_ab12cd34.png);
-- NULL means "fall back to company_logo_text", which is what every row already has.
--
-- Run it with:  mysql -u root practicore < migrations/013_employer_logo_upload.sql
--
-- Safe to run more than once (MariaDB IF NOT EXISTS syntax).

ALTER TABLE employers
    ADD COLUMN IF NOT EXISTS logo_path VARCHAR(255) NULL AFTER company_logo_text;