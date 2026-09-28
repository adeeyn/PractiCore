-- Durable competency profile. Today the per-domain breakdown only lives in the
-- Flask session, so it is lost on logout and the Random Forest ranker has no
-- per-domain features to train or score on. One row per student per domain,
-- upserted on every assessment attempt.
-- Safe to run more than once.

CREATE TABLE IF NOT EXISTS assessment_domain_scores (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT          NOT NULL,
    domain       VARCHAR(100) NOT NULL,
    correct      INT          NOT NULL DEFAULT 0,
    total        INT          NOT NULL DEFAULT 0,
    score_percent INT         NOT NULL DEFAULT 0,
    track_code   VARCHAR(20)  NULL,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_assessment_domain_student (student_id, domain),
    CONSTRAINT fk_assessment_domain_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Every completed attempt, so the trainer has history to learn from and so a
-- later attempt does not erase what the student demonstrated before.
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    student_id         INT          NOT NULL,
    overall_percentage INT          NOT NULL DEFAULT 0,
    total_correct      INT          NOT NULL DEFAULT 0,
    total_questions    INT          NOT NULL DEFAULT 0,
    competency_level   VARCHAR(60)  NULL,
    taken_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assessment_attempts_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    INDEX idx_assessment_attempts_student (student_id, taken_at)
) ENGINE=InnoDB;
