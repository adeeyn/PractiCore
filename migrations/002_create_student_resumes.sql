-- Store uploaded resumes in the database instead of uploads/resumes/.
-- Kept in its own table so reading `students` never loads the file bytes.
-- Safe to run more than once.

CREATE TABLE IF NOT EXISTS student_resumes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT          NOT NULL,
    filename    VARCHAR(255) NOT NULL,
    mime_type   VARCHAR(100) NOT NULL,
    file_size   INT          NOT NULL,
    file_data   MEDIUMBLOB   NOT NULL,  -- up to 16 MB
    uploaded_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_resumes_student (student_id),  -- one resume per student
    CONSTRAINT fk_student_resumes_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
) ENGINE=InnoDB;
