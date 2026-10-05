-- Administrator Module (CP2 sections 1.3.2 / 1.3.3 / 1.3.4).
--
-- Only two columns are genuinely missing. CP2's Administrator entity has no
-- table of its own: an administrator is a `users` row with role='admin', and a
-- partner company IS an `employers` row, so the module reuses both rather than
-- introducing a parallel structure.
--
-- Safe to run more than once.

-- Contact number for a partner company. CP2 has the administrator enter
-- "required company information" when creating the account, and the existing
-- employers table has no phone field.
ALTER TABLE employers
    ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(30) NULL AFTER contact_name;

-- Posting status, so the administrator can monitor postings as CP2 section
-- 1.3.4 requires ("review posted internship details to ensure that they follow
-- the system's guidelines"). Default 'active' keeps every existing posting
-- visible and ranked without a data backfill.
ALTER TABLE internship_postings
    ADD COLUMN IF NOT EXISTS status ENUM('active','closed') NOT NULL DEFAULT 'active' AFTER is_remote;

-- Index for the admin postings list, which filters on status and orders by date.
ALTER TABLE internship_postings
    ADD INDEX IF NOT EXISTS idx_posting_status (status, posted_date);
