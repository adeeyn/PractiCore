-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: practicore
-- ------------------------------------------------------
-- Server version	5.5.5-10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `applications`
--

DROP TABLE IF EXISTS `applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `applications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `posting_id` int(11) NOT NULL,
  `status` enum('Pending','In Review','Reviewed','Shortlisted','Scheduled','Hired','Rejected') NOT NULL DEFAULT 'Pending',
  `match_score` int(11) NOT NULL DEFAULT 0,
  `resume_match_score` tinyint(3) unsigned DEFAULT NULL,
  `assessment_match_score` tinyint(3) unsigned DEFAULT NULL,
  `employer_notes` text DEFAULT NULL,
  `applied_on` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_applications_student_posting` (`student_id`,`posting_id`),
  KEY `fk_applications_posting` (`posting_id`),
  CONSTRAINT `fk_applications_posting` FOREIGN KEY (`posting_id`) REFERENCES `internship_postings` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_applications_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=196 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `assessment_attempts`
--

DROP TABLE IF EXISTS `assessment_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_attempts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `posting_id` int(11) DEFAULT NULL,
  `attempt_no` int(11) NOT NULL DEFAULT 1,
  `overall_percentage` int(11) NOT NULL DEFAULT 0,
  `total_correct` int(11) NOT NULL DEFAULT 0,
  `total_questions` int(11) NOT NULL DEFAULT 0,
  `competency_level` varchar(60) DEFAULT NULL,
  `taken_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `started_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `submitted_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_attempt` (`student_id`,`attempt_no`,`posting_id`),
  KEY `idx_assessment_attempts_student` (`student_id`,`taken_at`),
  KEY `idx_attempt_student` (`student_id`),
  CONSTRAINT `fk_assessment_attempts_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `assessment_domain_scores`
--

DROP TABLE IF EXISTS `assessment_domain_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_domain_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `domain` varchar(100) NOT NULL,
  `correct` int(11) NOT NULL DEFAULT 0,
  `total` int(11) NOT NULL DEFAULT 0,
  `score_percent` int(11) NOT NULL DEFAULT 0,
  `track_code` varchar(20) DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_domain_student` (`student_id`,`domain`),
  CONSTRAINT `fk_assessment_domain_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `assessment_questions`
--

DROP TABLE IF EXISTS `assessment_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_questions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `question_code` varchar(30) DEFAULT NULL,
  `course_track` varchar(50) NOT NULL,
  `category` varchar(100) NOT NULL,
  `competency` varchar(100) DEFAULT NULL,
  `doc_competency` varchar(60) DEFAULT NULL,
  `set_id` int(11) DEFAULT NULL,
  `target_role` varchar(100) NOT NULL,
  `pathway` varchar(100) DEFAULT NULL,
  `source_type` enum('Researcher-Developed','Framework-Derived','Research-Supported','Validation-Approved') DEFAULT NULL,
  `key_status` varchar(20) NOT NULL DEFAULT 'Verified',
  `question_type` varchar(40) NOT NULL DEFAULT 'Multiple Choice',
  `difficulty` enum('easy','medium','hard') NOT NULL DEFAULT 'medium',
  `standard_ref` varchar(100) NOT NULL,
  `question_text` text NOT NULL,
  `option_a` text NOT NULL,
  `option_b` text NOT NULL,
  `option_c` text NOT NULL,
  `option_d` text NOT NULL,
  `correct_option` char(1) NOT NULL,
  `explanation` text DEFAULT NULL,
  `model_answer` varchar(255) DEFAULT NULL,
  `option_json` text DEFAULT NULL,
  `position` int(11) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_questions_code` (`question_code`),
  KEY `idx_assessment_questions_pool` (`is_active`,`competency`,`difficulty`),
  KEY `idx_assessment_questions_active` (`is_active`,`question_code`)
) ENGINE=InnoDB AUTO_INCREMENT=1462 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attempt_competencies`
--

DROP TABLE IF EXISTS `attempt_competencies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempt_competencies` (
  `attempt_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `set_id` int(11) DEFAULT NULL,
  `correct_count` int(11) NOT NULL DEFAULT 0,
  `question_count` int(11) NOT NULL DEFAULT 0,
  `score_percent` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`attempt_id`,`competency_code`),
  KEY `fk_ac_competency` (`competency_code`),
  CONSTRAINT `fk_ac_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ac_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attempt_questions`
--

DROP TABLE IF EXISTS `attempt_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempt_questions` (
  `attempt_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `display_order` int(11) NOT NULL DEFAULT 0,
  `selected_answer` varchar(255) DEFAULT NULL,
  `is_correct` tinyint(1) NOT NULL DEFAULT 0,
  `answered_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`attempt_id`,`question_id`),
  KEY `idx_aq_question` (`question_id`,`attempt_id`),
  CONSTRAINT `fk_aq_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_aq_question` FOREIGN KEY (`question_id`) REFERENCES `assessment_questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `compatibility_scores`
--

DROP TABLE IF EXISTS `compatibility_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `compatibility_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `posting_id` int(11) NOT NULL,
  `assessment_score` int(11) NOT NULL DEFAULT 0,
  `evidence_score` int(11) NOT NULL DEFAULT 0,
  `total_score` int(11) NOT NULL DEFAULT 0,
  `competencies_met` int(11) NOT NULL DEFAULT 0,
  `competencies_total` int(11) NOT NULL DEFAULT 0,
  `detail` text DEFAULT NULL,
  `computed_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_compat` (`student_id`,`posting_id`),
  KEY `fk_cs_posting` (`posting_id`),
  CONSTRAINT `fk_cs_posting` FOREIGN KEY (`posting_id`) REFERENCES `internship_postings` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cs_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `competencies`
--

DROP TABLE IF EXISTS `competencies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `competencies` (
  `code` varchar(30) NOT NULL,
  `name` varchar(100) NOT NULL,
  `track` varchar(50) NOT NULL,
  `is_core` tinyint(1) NOT NULL DEFAULT 0,
  `description` varchar(255) DEFAULT NULL,
  `sort_order` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `competency_skill_map`
--

DROP TABLE IF EXISTS `competency_skill_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `competency_skill_map` (
  `skill_key` varchar(60) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `strength` enum('primary','supporting') NOT NULL DEFAULT 'supporting',
  PRIMARY KEY (`skill_key`,`competency_code`),
  KEY `idx_csm_competency` (`competency_code`),
  CONSTRAINT `fk_csm_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `employers`
--

DROP TABLE IF EXISTS `employers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `company_name` varchar(150) NOT NULL,
  `company_logo_text` varchar(255) DEFAULT NULL,
  `logo_path` varchar(255) DEFAULT NULL,
  `industry` varchar(120) DEFAULT NULL,
  `location` varchar(100) NOT NULL,
  `about` text DEFAULT NULL,
  `required_skills` text DEFAULT NULL,
  `contact_name` varchar(100) DEFAULT NULL,
  `contact_phone` varchar(30) DEFAULT NULL,
  `contact_position` varchar(100) DEFAULT NULL,
  `website` varchar(150) DEFAULT NULL,
  `company_size` varchar(50) DEFAULT NULL,
  `is_hiring` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_employers_user_id` (`user_id`),
  CONSTRAINT `fk_employers_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `internship_competency_requirements`
--

DROP TABLE IF EXISTS `internship_competency_requirements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_competency_requirements` (
  `posting_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `importance` enum('essential','preferred') NOT NULL DEFAULT 'preferred',
  `required_percent` int(11) NOT NULL DEFAULT 60,
  PRIMARY KEY (`posting_id`,`competency_code`),
  KEY `idx_icr_competency` (`competency_code`),
  CONSTRAINT `fk_icr_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE,
  CONSTRAINT `fk_icr_posting` FOREIGN KEY (`posting_id`) REFERENCES `internship_postings` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `internship_postings`
--

DROP TABLE IF EXISTS `internship_postings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_postings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employer_id` int(11) NOT NULL,
  `title` varchar(150) NOT NULL,
  `department` varchar(100) DEFAULT NULL,
  `description` text NOT NULL,
  `is_remote` tinyint(1) DEFAULT 0,
  `status` enum('active','closed') NOT NULL DEFAULT 'active',
  `positions_available` int(11) NOT NULL DEFAULT 1,
  `posted_date` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `employer_id` (`employer_id`),
  KEY `idx_posting_status` (`status`,`posted_date`),
  CONSTRAINT `internship_postings_ibfk_1` FOREIGN KEY (`employer_id`) REFERENCES `employers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `posting_skills`
--

DROP TABLE IF EXISTS `posting_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `posting_skills` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `posting_id` int(11) NOT NULL,
  `skill_name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `posting_id` (`posting_id`),
  CONSTRAINT `posting_skills_ibfk_1` FOREIGN KEY (`posting_id`) REFERENCES `internship_postings` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=422 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_exposure_history`
--

DROP TABLE IF EXISTS `question_exposure_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_exposure_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `set_id` int(11) NOT NULL,
  `attempt_id` int(11) DEFAULT NULL,
  `exposed_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_exposure_student` (`student_id`,`competency_code`),
  KEY `fk_exposure_set` (`set_id`),
  CONSTRAINT `fk_exposure_set` FOREIGN KEY (`set_id`) REFERENCES `question_sets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exposure_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_key_corrections`
--

DROP TABLE IF EXISTS `question_key_corrections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_key_corrections` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `question_code` varchar(30) NOT NULL,
  `recorded_option` char(1) NOT NULL,
  `applied_option` char(1) NOT NULL,
  `recorded_option_text` varchar(255) DEFAULT NULL,
  `applied_option_text` varchar(255) DEFAULT NULL,
  `explanation` text DEFAULT NULL,
  `rule` varchar(80) NOT NULL DEFAULT 'explanation-token-match',
  `source_document` varchar(120) NOT NULL DEFAULT 'PractiCore_Final_Research_Based_Question_Bank.docx',
  `corrected_by` varchar(80) NOT NULL DEFAULT 'flask seed-master-bank',
  `corrected_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key_correction` (`question_code`),
  CONSTRAINT `fk_key_correction_question` FOREIGN KEY (`question_code`) REFERENCES `assessment_questions` (`question_code`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_seen_history`
--

DROP TABLE IF EXISTS `question_seen_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_seen_history` (
  `student_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `attempt_id` int(11) DEFAULT NULL,
  `times_seen` int(11) NOT NULL DEFAULT 1,
  `last_seen_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`student_id`,`question_id`),
  KEY `idx_qsh_student` (`student_id`,`competency_code`),
  KEY `idx_qsh_stale` (`student_id`,`competency_code`,`last_seen_at`),
  KEY `fk_qsh_question` (`question_id`),
  KEY `fk_qsh_competency` (`competency_code`),
  CONSTRAINT `fk_qsh_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE,
  CONSTRAINT `fk_qsh_question` FOREIGN KEY (`question_id`) REFERENCES `assessment_questions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_qsh_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_set_members`
--

DROP TABLE IF EXISTS `question_set_members`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_set_members` (
  `set_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  PRIMARY KEY (`set_id`,`question_id`),
  KEY `idx_qsm_question` (`question_id`),
  CONSTRAINT `fk_qsm_question` FOREIGN KEY (`question_id`) REFERENCES `assessment_questions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_qsm_set` FOREIGN KEY (`set_id`) REFERENCES `question_sets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_sets`
--

DROP TABLE IF EXISTS `question_sets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_sets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `competency_code` varchar(30) NOT NULL,
  `set_code` char(1) NOT NULL,
  `label` varchar(60) NOT NULL,
  `question_count` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_competency_set` (`competency_code`,`set_code`),
  CONSTRAINT `fqs_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=251 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resume_competency_evidence`
--

DROP TABLE IF EXISTS `resume_competency_evidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resume_competency_evidence` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `evidence_skills` text NOT NULL,
  `evidence_count` int(11) NOT NULL DEFAULT 0,
  `has_project` tinyint(1) NOT NULL DEFAULT 0,
  `has_experience` tinyint(1) NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_resume_evidence` (`student_id`,`competency_code`),
  KEY `fk_rce_competency` (`competency_code`),
  CONSTRAINT `fk_rce_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE,
  CONSTRAINT `fk_rce_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=103 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `student_competency_scores`
--

DROP TABLE IF EXISTS `student_competency_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_competency_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `competency_code` varchar(30) NOT NULL,
  `score_percent` int(11) NOT NULL DEFAULT 0,
  `attempts_count` int(11) NOT NULL DEFAULT 0,
  `best_percent` int(11) NOT NULL DEFAULT 0,
  `last_attempt_id` int(11) DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_competency` (`student_id`,`competency_code`),
  KEY `fk_scs_competency` (`competency_code`),
  CONSTRAINT `fk_scs_competency` FOREIGN KEY (`competency_code`) REFERENCES `competencies` (`code`) ON DELETE CASCADE,
  CONSTRAINT `fk_scs_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=67 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `student_resumes`
--

DROP TABLE IF EXISTS `student_resumes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_resumes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `mime_type` varchar(100) NOT NULL,
  `file_size` int(11) NOT NULL,
  `education` text DEFAULT NULL,
  `certifications` text DEFAULT NULL,
  `experience` text DEFAULT NULL,
  `projects` text DEFAULT NULL,
  `file_data` mediumblob NOT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_resumes_student` (`student_id`),
  CONSTRAINT `fk_student_resumes_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `student_no` varchar(20) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `email` varchar(120) NOT NULL,
  `name` varchar(100) NOT NULL,
  `course` varchar(120) NOT NULL,
  `skills` text DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `year_level` varchar(20) DEFAULT '4th Year',
  `avatar_path` varchar(255) DEFAULT NULL,
  `resume_path` varchar(255) DEFAULT NULL,
  `assessment_score` int(11) DEFAULT 0,
  `total_questions` int(11) DEFAULT 0,
  `competency_level` varchar(50) DEFAULT 'Not Assessed',
  `resume_match_rate` int(11) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_no` (`student_no`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `uq_students_user_id` (`user_id`),
  CONSTRAINT `fk_students_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=999902 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(120) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('student','employer','admin') NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-06  7:29:40
