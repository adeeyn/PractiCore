-- Splits the stored match score into its two reported halves.
--
-- `applications.match_score` is the single number the ranking sorts by, and it
-- stays exactly that: nothing about the ordering changes. But it is a weighted
-- blend of two very different things - how much of the posting's required skill
-- list the resume proves, and how the student actually scored on the objective
-- items. Showing only the blend hides which half is carrying (or sinking) an
-- applicant, so the two components are stored beside it.
--
-- NULL means "not computed yet", never zero: both are written when a student
-- applies, and `flask --app app backfill-match-components` fills in the rows that
-- predate this migration. The templates hide the split while they are NULL rather
-- than printing a 0% the applicant never earned.
--
-- Safe to run more than once.

ALTER TABLE applications
    ADD COLUMN IF NOT EXISTS resume_match_score TINYINT UNSIGNED NULL AFTER match_score,
    ADD COLUMN IF NOT EXISTS assessment_match_score TINYINT UNSIGNED NULL AFTER resume_match_score;
