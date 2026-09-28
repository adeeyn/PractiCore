-- The research-based question bank identifies each item by its published code
-- (Q01..Q43) and records the sub-domain and pathway it was written for, so a
-- result can be traced back to the source document and the faculty validation.
-- Safe to run more than once (MariaDB IF NOT EXISTS syntax).

ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS question_code VARCHAR(10)  NULL AFTER id,
    ADD COLUMN IF NOT EXISTS competency    VARCHAR(100) NULL AFTER category,
    ADD COLUMN IF NOT EXISTS pathway      VARCHAR(100) NULL AFTER target_role;

-- One row per published item; re-running the seeder is idempotent.
CREATE UNIQUE INDEX IF NOT EXISTS uq_assessment_questions_code
    ON assessment_questions (question_code);
