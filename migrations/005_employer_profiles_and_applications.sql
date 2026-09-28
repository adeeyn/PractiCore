-- What a partner-company employer account can fill in and keep updated.
-- Covers the employer pages in the CP2 write-up: Company Profile Management
-- (industry, about, the skills the company is looking for) plus the HR contact
-- shown in the topbar. Safe to run more than once (MariaDB IF NOT EXISTS syntax).

ALTER TABLE employers
    ADD COLUMN IF NOT EXISTS industry         VARCHAR(120) NULL AFTER company_logo_text,
    ADD COLUMN IF NOT EXISTS about            TEXT         NULL AFTER location,
    -- Comma separated, the same shape as students.skills
    ADD COLUMN IF NOT EXISTS required_skills   TEXT         NULL AFTER about,
    ADD COLUMN IF NOT EXISTS contact_name      VARCHAR(100) NULL AFTER required_skills,
    ADD COLUMN IF NOT EXISTS contact_position  VARCHAR(100) NULL AFTER contact_name,
    ADD COLUMN IF NOT EXISTS website           VARCHAR(150) NULL AFTER contact_position,
    ADD COLUMN IF NOT EXISTS company_size      VARCHAR(50)  NULL AFTER website,
    ADD COLUMN IF NOT EXISTS is_hiring         TINYINT(1)   NOT NULL DEFAULT 1 AFTER company_size;

-- Extra details an employer enters on the Internship Posting page.
ALTER TABLE internship_postings
    ADD COLUMN IF NOT EXISTS department         VARCHAR(100) NULL AFTER title,
    ADD COLUMN IF NOT EXISTS positions_available INT         NOT NULL DEFAULT 1 AFTER is_remote;

-- One row per student applying to a posting. The employer screening, ranking
-- and management pages read this table instead of placeholder lists.
CREATE TABLE IF NOT EXISTS applications (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT          NOT NULL,
    posting_id     INT          NOT NULL,
    status         ENUM('Pending', 'In Review', 'Reviewed', 'Shortlisted',
                       'Scheduled', 'Hired', 'Rejected') NOT NULL DEFAULT 'Pending',
    match_score    INT          NOT NULL DEFAULT 0,
    employer_notes TEXT         NULL,
    applied_on     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_applications_student_posting (student_id, posting_id),
    CONSTRAINT fk_applications_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_applications_posting FOREIGN KEY (posting_id) REFERENCES internship_postings (id) ON DELETE CASCADE
) ENGINE=InnoDB;
