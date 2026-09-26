-- Per-question difficulty, used for the per-question assessment timer.
-- Safe to run more than once: the seeding UPDATE only touches rows without a difficulty,
-- so difficulties edited by hand are never overwritten.

ALTER TABLE assessment_questions
    ADD COLUMN IF NOT EXISTS difficulty ENUM('easy', 'medium', 'hard') NULL AFTER question_type;

-- Starting values (adjust individual questions afterwards as needed):
--   Scenario questions                     -> hard
--   Conceptual with long question/options  -> medium
--   Short conceptual questions             -> easy
UPDATE assessment_questions
SET difficulty = CASE
    WHEN question_type = 'Scenario' THEN 'hard'
    WHEN LENGTH(question_text)
         + GREATEST(LENGTH(option_a), LENGTH(option_b), LENGTH(option_c), LENGTH(option_d)) > 120 THEN 'medium'
    ELSE 'easy'
END
WHERE difficulty IS NULL;

ALTER TABLE assessment_questions
    MODIFY difficulty ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium';
