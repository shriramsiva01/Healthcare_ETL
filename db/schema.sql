-- ============================================================
-- Healthcare ETL — MySQL Database Schema
-- ============================================================
-- Run this file to set up the complete database:
--   mysql -u root -p < db/schema.sql
-- ============================================================

-- ── Create Database ─────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS healthcare_etl
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE healthcare_etl;

-- ══════════════════════════════════════════════════════════════
--  TABLE 1: patients (parent table)
-- ══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS diagnoses;
DROP TABLE IF EXISTS encounters;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS pipeline_runs;

CREATE TABLE patients (
    patient_id    INT          NOT NULL,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    date_of_birth VARCHAR(10)  DEFAULT NULL,
    gender        VARCHAR(10)  DEFAULT NULL,
    phone_masked  VARCHAR(64)  DEFAULT NULL,
    ssn_masked    VARCHAR(64)  DEFAULT NULL,
    address       VARCHAR(255) DEFAULT NULL,
    city          VARCHAR(100) DEFAULT NULL,
    state         VARCHAR(50)  DEFAULT NULL,
    zip           VARCHAR(10)  DEFAULT NULL,
    age           INT          DEFAULT NULL,
    age_group     VARCHAR(20)  DEFAULT NULL,
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Primary key
    PRIMARY KEY (patient_id),

    -- Indexes for common lookups
    INDEX idx_patient_name (last_name, first_name),
    INDEX idx_patient_state (state),
    INDEX idx_patient_age_group (age_group),
    INDEX idx_patient_gender (gender)
) ENGINE=InnoDB;


-- ══════════════════════════════════════════════════════════════
--  TABLE 2: encounters (child of patients)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE encounters (
    encounter_id   INT          NOT NULL,
    patient_id     INT          NOT NULL,
    encounter_date VARCHAR(10)  DEFAULT NULL,
    encounter_type VARCHAR(50)  DEFAULT NULL,
    provider_name  VARCHAR(150) DEFAULT NULL,
    facility       VARCHAR(200) DEFAULT NULL,
    created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,

    -- Primary key
    PRIMARY KEY (encounter_id),

    -- Foreign key → patients
    CONSTRAINT fk_encounter_patient
        FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Indexes
    INDEX idx_encounter_patient (patient_id),
    INDEX idx_encounter_date (encounter_date),
    INDEX idx_encounter_type (encounter_type),
    INDEX idx_encounter_facility (facility(50))
) ENGINE=InnoDB;


-- ══════════════════════════════════════════════════════════════
--  TABLE 3: diagnoses (child of encounters)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE diagnoses (
    diagnosis_id     INT          NOT NULL,
    encounter_id     INT          NOT NULL,
    icd_code         VARCHAR(10)  DEFAULT NULL,
    description      VARCHAR(255) DEFAULT NULL,
    severity         VARCHAR(20)  DEFAULT NULL,
    icd_valid        BOOLEAN      DEFAULT TRUE,
    disease_category VARCHAR(50)  DEFAULT NULL,
    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,

    -- Primary key
    PRIMARY KEY (diagnosis_id),

    -- Foreign key → encounters
    CONSTRAINT fk_diagnosis_encounter
        FOREIGN KEY (encounter_id)
        REFERENCES encounters(encounter_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Indexes
    INDEX idx_diagnosis_encounter (encounter_id),
    INDEX idx_diagnosis_icd (icd_code),
    INDEX idx_diagnosis_category (disease_category),
    INDEX idx_diagnosis_severity (severity)
) ENGINE=InnoDB;


-- ══════════════════════════════════════════════════════════════
--  TABLE 4: pipeline_runs (audit/monitoring — standalone)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE pipeline_runs (
    run_id           INT AUTO_INCREMENT PRIMARY KEY,
    pipeline_name    VARCHAR(50)  NOT NULL,
    status           VARCHAR(20)  NOT NULL,
    rows_extracted   INT          DEFAULT 0,
    rows_transformed INT          DEFAULT 0,
    rows_loaded      INT          DEFAULT 0,
    duration_seconds FLOAT        DEFAULT 0.0,
    error_message    TEXT         DEFAULT NULL,
    started_at       DATETIME     DEFAULT NULL,
    completed_at     DATETIME     DEFAULT NULL,

    -- Indexes
    INDEX idx_run_name (pipeline_name),
    INDEX idx_run_status (status),
    INDEX idx_run_completed (completed_at)
) ENGINE=InnoDB;


-- ══════════════════════════════════════════════════════════════
--  VERIFICATION: Show created tables
-- ══════════════════════════════════════════════════════════════

SELECT '✅ Database healthcare_etl created successfully!' AS status;
SHOW TABLES;
