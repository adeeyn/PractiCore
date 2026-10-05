-- Competency-driven assessment and cross-matching.
--
-- The previous design picked questions by JOB CATEGORY, so a student was
-- measured against categories their resume or target internship never asked
-- for. This schema keys everything on a COMPETENCY instead, which is what both
-- the resume evidence and an internship requirement can be mapped onto.
--
-- Safe to run more than once (MariaDB IF NOT EXISTS syntax).

-- ---------- Taxonomy ----------

CREATE TABLE IF NOT EXISTS competencies (
    code        VARCHAR(30)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    track       VARCHAR(50)  NOT NULL,   -- PractiCore job category, for reporting only
    is_core     TINYINT(1)   NOT NULL DEFAULT 0,
    description VARCHAR(255) NULL,
    sort_order  INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (code)
) ENGINE=InnoDB;

-- One skill can evidence several competencies (JavaScript -> WEB and PROG), and
-- one competency is evidenced by several skills, so this is many-to-many.
CREATE TABLE IF NOT EXISTS competency_skill_map (
    skill_key       VARCHAR(60)  NOT NULL,  -- lower-cased skill name
    competency_code VARCHAR(30)  NOT NULL,
    strength        ENUM('primary', 'supporting') NOT NULL DEFAULT 'supporting',
    PRIMARY KEY (skill_key, competency_code),
    INDEX idx_csm_competency (competency_code),
    CONSTRAINT fk_csm_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- What an internship actually asks for. importance lets a posting say
-- "Networking is essential here" without hard-coding weights per posting.
CREATE TABLE IF NOT EXISTS internship_competency_requirements (
    posting_id       INT         NOT NULL,
    competency_code  VARCHAR(30) NOT NULL,
    importance       ENUM('essential', 'preferred') NOT NULL DEFAULT 'preferred',
    required_percent INT         NOT NULL DEFAULT 60,
    PRIMARY KEY (posting_id, competency_code),
    INDEX idx_icr_competency (competency_code),
    CONSTRAINT fk_icr_posting FOREIGN KEY (posting_id)
        REFERENCES internship_postings (id) ON DELETE CASCADE,
    CONSTRAINT fk_icr_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;


-- ---------- Parallel question forms ----------

-- Three equivalent forms per competency. The three must measure the same
-- competency at comparable difficulty; they differ in wording and scenario so a
-- student cannot simply memorise an answer from a previous sitting.
CREATE TABLE IF NOT EXISTS question_sets (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    competency_code VARCHAR(30) NOT NULL,
    set_code        CHAR(1)     NOT NULL,          -- A / B / C
    label           VARCHAR(60) NOT NULL,          -- never shown to students
    question_count  INT         NOT NULL DEFAULT 0,
    UNIQUE KEY uq_competency_set (competency_code, set_code),
    CONSTRAINT fqs_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- A question can legitimately measure more than one competency. Q22 (systematic
-- fault isolation) belongs in the Networking form AND the Troubleshooting form,
-- and Q02 (debugging approach) in both Programming and Problem Solving.
--
-- assessment_questions.set_id (added below) can only hold ONE form, so a
-- borrowed item was silently reassigned to whichever competency was seeded last,
-- leaving the other form short. A membership table expresses the real
-- many-to-many relationship and is what the seeder now writes.
CREATE TABLE IF NOT EXISTS question_set_members (
    set_id      INT         NOT NULL,
    question_id INT         NOT NULL,
    PRIMARY KEY (set_id, question_id),
    INDEX idx_qsm_question (question_id),
    CONSTRAINT fk_qsm_set FOREIGN KEY (set_id)
        REFERENCES question_sets (id) ON DELETE CASCADE,
    CONSTRAINT fk_qsm_question FOREIGN KEY (question_id)
        REFERENCES assessment_questions (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- The published research bank is kept as Set A. Migration 008 already added
-- `competency`; this adds the form it belongs to.
ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS set_id INT NULL AFTER competency;

-- Parallel-form codes look like PF-TROUBLE-B1 (14 characters). Migration 008
-- created this column as varchar(10), which silently truncated every code longer
-- than 10 characters, so all four items for one competency collided on a single
-- key and the form lost questions without any error. Widened so a long
-- competency name can never corrupt the bank.
ALTER TABLE assessment_questions
    MODIFY COLUMN question_code VARCHAR(30) NULL;

-- ---------- Attempts and results ----------

-- One row per sitting. posting_id is NULL for a general assessment, and set when
-- the student is assessing for a specific internship, which is what makes the
-- assessment adaptive.
--
-- NOTE: assessment_attempts already existed from migration 006 with a narrower
-- shape (no posting_id, no attempt_no, and taken_at rather than started_at).
-- CREATE TABLE IF NOT EXISTS below is a no-op against that table, so the extra
-- columns are added separately and are what make this table adaptive.
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT         NOT NULL,
    posting_id        INT         NULL,
    attempt_no        INT         NOT NULL DEFAULT 1,
    total_questions   INT         NOT NULL DEFAULT 0,
    total_correct     INT         NOT NULL DEFAULT 0,
    overall_percent   INT         NOT NULL DEFAULT 0,
    competency_level  VARCHAR(60) NULL,
    started_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at      TIMESTAMP   NULL,
    UNIQUE KEY uq_attempt (student_id, attempt_no, posting_id),
    INDEX idx_attempt_student (student_id),
    CONSTRAINT fk_attempt_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_posting FOREIGN KEY (posting_id)
        REFERENCES internship_postings (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bring the pre-existing table (migration 006) up to the adaptive shape.
-- 006 named the score column overall_percentage; the adaptive writer uses that
-- same name, so it is left alone here.
ALTER TABLE assessment_attempts
    ADD COLUMN IF NOT EXISTS posting_id INT NULL AFTER student_id;
ALTER TABLE assessment_attempts
    ADD COLUMN IF NOT EXISTS attempt_no INT NOT NULL DEFAULT 1 AFTER posting_id;
ALTER TABLE assessment_attempts
    ADD COLUMN IF NOT EXISTS taken_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE assessment_attempts
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE assessment_attempts
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP NULL;
ALTER TABLE assessment_attempts
    ADD INDEX IF NOT EXISTS idx_attempt_student (student_id);

-- The per-competency result, and which form was used to obtain it. This is the
-- unit the cross-matcher reads. The composite key is the natural key: one row
-- per competency per attempt.
CREATE TABLE IF NOT EXISTS attempt_competencies (
    attempt_id      INT         NOT NULL,
    competency_code VARCHAR(30) NOT NULL,
    set_id          INT         NULL,
    correct_count   INT         NOT NULL DEFAULT 0,
    question_count  INT         NOT NULL DEFAULT 0,
    score_percent   INT         NOT NULL DEFAULT 0,
    PRIMARY KEY (attempt_id, competency_code),
    CONSTRAINT fk_ac_attempt FOREIGN KEY (attempt_id)
        REFERENCES assessment_attempts (id) ON DELETE CASCADE,
    CONSTRAINT fk_ac_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Anti-repeat ledger. Records the FORM a student was shown, not just the
-- questions, so a retake can prefer a form they have never seen even when the
-- underlying items are regenerated.
CREATE TABLE IF NOT EXISTS question_exposure_history (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT         NOT NULL,
    competency_code VARCHAR(30) NOT NULL,
    set_id          INT         NOT NULL,
    attempt_id      INT         NULL,
    exposed_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_exposure_student (student_id, competency_code),
    CONSTRAINT fk_exposure_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_exposure_set FOREIGN KEY (set_id)
        REFERENCES question_sets (id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- ---------- Student competency profile ----------

-- The durable per-competency record the cross-matcher reads. This is the
-- "demonstrated" half of the evidence: it is written from assessment results,
-- never from a resume claim.
CREATE TABLE IF NOT EXISTS student_competency_scores (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT         NOT NULL,
    competency_code  VARCHAR(30) NOT NULL,
    score_percent    INT         NOT NULL DEFAULT 0,
    attempts_count   INT         NOT NULL DEFAULT 0,
    best_percent     INT         NOT NULL DEFAULT 0,
    last_attempt_id  INT         NULL,
    updated_at       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_competency (student_id, competency_code),
    CONSTRAINT fk_scs_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_scs_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Resume evidence, stored SEPARATELY from scores on purpose: a skill named on a
-- resume is a claim. It can corroborate an assessment result but must never
-- create one.
CREATE TABLE IF NOT EXISTS resume_competency_evidence (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT         NOT NULL,
    competency_code VARCHAR(30) NOT NULL,
    evidence_skills TEXT        NOT NULL,   -- comma separated, as extracted
    evidence_count  INT         NOT NULL DEFAULT 0,
    has_project     TINYINT(1)  NOT NULL DEFAULT 0,
    has_experience  TINYINT(1)  NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_resume_evidence (student_id, competency_code),
    CONSTRAINT fk_rce_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_rce_competency FOREIGN KEY (competency_code)
        REFERENCES competencies (code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------- Cross-match result ----------

-- One row per (student, posting). Kept so the ranking has a stable, auditable
-- number instead of recomputing (and possibly disagreeing) on every page load.
CREATE TABLE IF NOT EXISTS compatibility_scores (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT         NOT NULL,
    posting_id        INT         NOT NULL,
    assessment_score  INT         NOT NULL DEFAULT 0,  -- required-competency coverage
    evidence_score    INT         NOT NULL DEFAULT 0,  -- resume corroboration
    total_score       INT         NOT NULL DEFAULT 0,
    competencies_met  INT         NOT NULL DEFAULT 0,
    competencies_total INT        NOT NULL DEFAULT 0,
    detail            TEXT        NULL,                 -- JSON, for the explain panel
    computed_at       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_compat (student_id, posting_id),
    CONSTRAINT fk_cs_student FOREIGN KEY (student_id)
        REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_cs_posting FOREIGN KEY (posting_id)
        REFERENCES internship_postings (id) ON DELETE CASCADE
) ENGINE=InnoDB;
