-- 130-question competency master bank.
--
-- Everything here is ADDITIVE. No table is dropped, renamed or recreated, and no
-- existing row is deleted or modified: the 79 published items (43 research + 36
-- parallel-form) keep their ids, so every attempt_competencies / question_set_members
-- / question_exposure_history row that points at them stays valid.
--
-- Run it with:  mysql -u root practicore < migrations/012_master_question_bank.sql
--
-- Safe to run more than once (MariaDB IF NOT EXISTS / ON DUPLICATE KEY syntax).

-- ---------- 1. Question metadata the master bank needs ----------

-- 1a. Provenance / audit.
--
-- Deliberately does NOT include a 'CP2' value. CP2 in this project is the capstone
-- WRITE-UP (referenced as "CP2 section 1.3.1 / Figure 20" in the admin routes); it
-- is not a question bank. services/research_bank.py states plainly that the 43 items
-- are PractiCore's own, with SFIA/CompTIA/Google/Cisco used as competency
-- *references* only. A 'CP2' source label would be a fabricated citation, so the
-- enum omits it. The column can be widened later if real evidence appears.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS source_type ENUM(
        'Researcher-Developed',
        'Framework-Derived',
        'Research-Supported',
        'Validation-Approved'
    ) NULL DEFAULT NULL AFTER pathway;

-- 1b. The rationale shown after grading, and the free-text / ordering payloads.
--
--     explanation : why the keyed option is right.
--     model_answer: expected short-answer text (used by 'Short Answer' items).
--     option_json : JSON array for 'Ordering' items, whose choices are not a fixed A-D.
--     position    : the correct index for 'Ordering' items, else NULL.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS explanation   TEXT         NULL AFTER correct_option,
    ADD COLUMN IF NOT EXISTS model_answer VARCHAR(255) NULL AFTER explanation,
    ADD COLUMN IF NOT EXISTS option_json  TEXT         NULL AFTER model_answer,
    ADD COLUMN IF NOT EXISTS position     INT          NULL AFTER option_json;

-- 1c. Retiring an item without deleting it, so old attempts stay explainable.
--     The default keeps every existing row active; the seeder never turns one off.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER position;

-- Answer-key audit trail for the researcher question bank.
--
-- The published document (PractiCore_Final_Research_Based_Question_Bank.docx)
-- records a "Correct Answer" letter AND an explanation that restates the correct
-- option. On audit, 64 of its 130 items had a key that contradicted their own
-- explanation - e.g. PROG-001 is keyed "A" ("Store only one value") for the
-- purpose of a loop, while its explanation says "Repeat instructions" (B).
--
-- Those items are corrected to the letter their own explanation supports. This
-- table records EVERY correction so the change is auditable and reversible: the
-- as-published key is preserved here before it is overridden.
--
-- Items whose key could not be adjudicated with confidence are NOT corrected and
-- NOT served; they are stored with is_active = 0 pending researcher review.
--
-- Additive only. Safe to run more than once.

-- One row per corrected item. `recorded_option` is what the document said;
-- `applied_option` is what the bank now grades against.
CREATE TABLE IF NOT EXISTS question_key_corrections (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    question_code       VARCHAR(30)  NOT NULL,
    recorded_option     CHAR(1)      NOT NULL,
    applied_option      CHAR(1)      NOT NULL,
    recorded_option_text VARCHAR(255) NULL,
    applied_option_text VARCHAR(255)  NULL,
    explanation         TEXT          NULL,
    rule                VARCHAR(80)   NOT NULL DEFAULT 'explanation-token-match',
    source_document     VARCHAR(120)  NOT NULL DEFAULT 'PractiCore_Final_Research_Based_Question_Bank.docx',
    corrected_by        VARCHAR(80)   NOT NULL DEFAULT 'flask seed-master-bank',
    corrected_at        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_key_correction (question_code),
    CONSTRAINT fk_key_correction_question FOREIGN KEY (question_code)
        REFERENCES assessment_questions (question_code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- The competency the document used, kept beside PractiCore's canonical code so an
-- item can always be traced back to the source document's own taxonomy even where
-- the two use different labels for the same area.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS doc_competency VARCHAR(60) NULL AFTER competency;

-- The item's own status in the source document, stored rather than discarded.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS key_status VARCHAR(20) NOT NULL DEFAULT 'Verified'
        AFTER source_type;

-- 'question_type' was VARCHAR(20). The master bank needs 'Scenario-Based Multiple
-- Choice', which is 30 characters and would be silently truncated to
-- 'Scenario-Based Multi'. Widened, not replaced.
ALTER TABLE assessment_questions
    MODIFY COLUMN question_type VARCHAR(40) NOT NULL DEFAULT 'Multiple Choice';

-- `difficulty` is ENUM('easy','medium','hard') from migration 003 and already
-- expresses Easy / Moderate / Difficult. Deliberately NOT changed: rewriting the enum
-- would discard the meaning the 79 scored rows depend on, and 'medium' IS 'Moderate'.
-- The bank seeds a real spread across all three instead.

-- Selection indexes: the bank is queried by (active, competency, difficulty) every
-- time an assessment is assembled.
CREATE INDEX IF NOT EXISTS idx_assessment_questions_pool
    ON assessment_questions (is_active, competency, difficulty);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_active
    ON assessment_questions (is_active, question_code);

-- ---------- 2. The four competencies the taxonomy could not express ----------
--
-- Migration 009 created `competencies` with `code` as the primary key. These four are
-- INSERTS, not a new table: the 13 requested competencies map onto the 14 that
-- already exist (PROG, OOP, DSA, DB, WEB, DEV, GIT, NET, SEC, CLOUD, DATA, PROB,
-- COMM), and only these four had no home.
--
-- is_core stays 0: the assessed-everywhere core remains the existing five
-- (PROG, PROB, DB, NET, COMM). Widening it would change every current student's
-- assessment shape.

INSERT INTO competencies (code, name, track, is_core, description, sort_order) VALUES
    ('OOP',   'Object-Oriented Programming',  'Software & Application Development', 0,
     'Classes, encapsulation, inheritance, polymorphism and interface design.', 14),
    ('DSA',   'Data Structures & Algorithms', 'Software & Application Development', 0,
     'Choosing a structure for a workload; time and space complexity; recursion.', 15),
    ('GIT',   'Version Control / Git',        'Software & Application Development', 0,
     'Commits, branching, merging, conflict resolution and collaboration workflow.', 16),
    ('CLOUD', 'Cloud & DevOps Fundamentals',  'Systems, Infrastructure & Networks', 0,
     'Virtualisation, containers, CI/CD, deployment environments and IaC basics.', 17)
ON DUPLICATE KEY UPDATE
    name = VALUES(name), track = VALUES(track),
    description = VALUES(description), sort_order = VALUES(sort_order);

-- ---------- 3. Per-question history ----------
--
-- Until now a retake could only rotate at FORM level: question_exposure_history
-- stores (student, competency, set_id) and no answer, and an attempt stored no
-- question list at all -- the selection lived in the Flask session and was discarded
-- on submit. So the system could not answer "has this student seen item Q14, what did
-- they answer, and was it right?".
--
-- This table is that ledger. It is append-only: a retake adds rows and never rewrites
-- or deletes the history of an earlier sitting.
--
-- `display_order` records the position the item was actually served at, so a past
-- attempt's randomised order can be reconstructed (Phase 11 randomisation is
-- per-instance; the master question itself is never touched).
--
-- `selected_answer` keeps the raw submission, NULL for an unanswered item, so
-- "unanswered" stays distinguishable from "wrong".
CREATE TABLE IF NOT EXISTS attempt_questions (
    attempt_id      INT          NOT NULL,
    question_id     INT          NOT NULL,
    display_order   INT          NOT NULL DEFAULT 0,
    selected_answer VARCHAR(255) NULL,
    is_correct      TINYINT(1)   NOT NULL DEFAULT 0,
    answered_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attempt_id, question_id),
    INDEX idx_aq_question (question_id, attempt_id),
    CONSTRAINT fk_aq_attempt FOREIGN KEY (attempt_id)
        REFERENCES assessment_attempts (id) ON DELETE CASCADE,
    CONSTRAINT fk_aq_question FOREIGN KEY (question_id)
        REFERENCES assessment_questions (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Which items a student has been shown, at ITEM granularity rather than form
-- granularity. `times_seen` and `last_seen_at` are denormalised on purpose: the
-- retake selector needs "stalest item first" on every assembly, and rescanning the
-- attempt history each time would not scale. Updated with
-- INSERT ... ON DUPLICATE KEY UPDATE, never deleted.
CREATE TABLE IF NOT EXISTS question_seen_history (
    student_id      INT         NOT NULL,
    question_id     INT         NOT NULL,
    competency_code VARCHAR(30) NOT NULL,
    attempt_id      INT         NULL,
    times_seen      INT         NOT NULL DEFAULT 1,
    last_seen_at    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, question_id),
    INDEX idx_qsh_student (student_id, competency_code),
    INDEX idx_qsh_stale (student_id, competency_code, last_seen_at),
    CONSTRAINT fk_qsh_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_qsh_question FOREIGN KEY (question_id)
        REFERENCES assessment_questions (id) ON DELETE CASCADE,
    CONSTRAINT fk_qsh_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;
