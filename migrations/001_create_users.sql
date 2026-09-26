-- One shared login for students, employers and admins.
-- Safe to run more than once (MariaDB IF NOT EXISTS syntax).

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(120) NOT NULL UNIQUE,
    username      VARCHAR(50)  NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('student', 'employer', 'admin') NOT NULL,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Link student profiles to their login account
ALTER TABLE students
    ADD COLUMN IF NOT EXISTS user_id INT NULL AFTER id,
    ADD UNIQUE INDEX IF NOT EXISTS uq_students_user_id (user_id),
    ADD CONSTRAINT fk_students_user FOREIGN KEY IF NOT EXISTS (user_id) REFERENCES users (id) ON DELETE CASCADE,
    -- Passwords now live in users.password_hash
    MODIFY password_hash VARCHAR(255) NULL;

-- Link employer companies to their login account (created by an admin)
ALTER TABLE employers
    ADD COLUMN IF NOT EXISTS user_id INT NULL AFTER id,
    ADD UNIQUE INDEX IF NOT EXISTS uq_employers_user_id (user_id),
    ADD CONSTRAINT fk_employers_user FOREIGN KEY IF NOT EXISTS (user_id) REFERENCES users (id) ON DELETE SET NULL;

-- Move existing student logins into users
INSERT INTO users (email, username, password_hash, role, created_at)
SELECT s.email, s.username, s.password_hash, 'student', s.created_at
FROM students s
WHERE s.user_id IS NULL
  AND s.password_hash IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM users u WHERE u.email = s.email OR u.username = s.username);

UPDATE students s
JOIN users u ON u.username = s.username AND u.role = 'student'
SET s.user_id = u.id
WHERE s.user_id IS NULL;
