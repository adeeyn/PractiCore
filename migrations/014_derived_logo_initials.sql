-- Logo initials are no longer typed in: the employer Company Profile page and the
-- admin Partner Company form both dropped the field, and the initials are derived
-- from company_name by practicore/initials.py instead. This migration removes the
-- cap that used to go with that field and refreshes the rows written before it.
--
-- Run it with:  mysql -u root practicore < migrations/014_derived_logo_initials.sql
--
-- Safe to run more than once (MariaDB IF NOT EXISTS / MODIFY syntax).

-- 1. Widen the column.
--
-- The derived value is at most a couple of characters, so 10 was never actually
-- binding. It is widened anyway so the storage limit can never be the thing that
-- decides how a company is abbreviated.
ALTER TABLE employers
    MODIFY COLUMN company_logo_text VARCHAR(255) NULL DEFAULT NULL;

-- 2. Refresh the stored initials from the company name.
--
-- The seeder used to carry a hand-written logo_text per company, which is why
-- "DevPro Lab" was stored as DP rather than the DL the shared rule produces.
-- Only rows whose initials disagree with the rule are touched, so a company that
-- already matches is left exactly as it is.
--
-- First letters of the first two words of the name, uppercased. Written with
-- SUBSTRING_INDEX rather than a Python loop so it stays a plain SQL migration.
UPDATE employers
SET company_logo_text = UPPER(CONCAT(
        LEFT(SUBSTRING_INDEX(TRIM(company_name), ' ', 1), 1),
        LEFT(
            SUBSTRING_INDEX(
                SUBSTRING_INDEX(TRIM(company_name), ' ', 2),
                ' ',
                -1
            ),
            1
        )
    ))
WHERE company_name IS NOT NULL
  AND TRIM(company_name) <> ''
  AND NOT (company_logo_text <=> UPPER(CONCAT(
        LEFT(SUBSTRING_INDEX(TRIM(company_name), ' ', 1), 1),
        LEFT(
            SUBSTRING_INDEX(
                SUBSTRING_INDEX(TRIM(company_name), ' ', 2),
                ' ',
                -1
            ),
            1
        )
    )));

-- 3. A company with no name cannot have initials; NULL means "nothing to show"
--    and every template already falls back to a placeholder.
UPDATE employers
SET company_logo_text = NULL
WHERE company_name IS NULL
   OR TRIM(company_name) = '';
