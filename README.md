# Healthcare ETL Data Pipeline

A production-grade **Extract → Transform → Load** pipeline for healthcare data, built with **Python**, **Pandas**, **FastAPI**, and **MySQL**.

---

## 📁 Project Structure

```
ETL/
├── app/              # FastAPI application (routes, schemas)
├── etl/              # Core ETL engine
│   ├── extract.py    #   → Read CSV/JSON source files
│   ├── transform.py  #   → Clean, validate, enrich data
│   ├── load.py       #   → Insert into MySQL
│   └── pipeline.py   #   → Orchestrate E → T → L
├── db/               # Database layer
│   ├── schema.sql    #   → MySQL DDL (tables, indexes, FKs)
│   ├── connection.py #   → SQLAlchemy engine + health check
│   └── models.py     #   → ORM models
├── config/
│   └── settings.py   # Pydantic Settings (env-driven)
├── data/raw/         # Sample input data
├── tests/            # Unit + integration tests
├── .env              # Database credentials (not committed)
└── requirements.txt  # Python dependencies
```

---

## 🚀 Step-by-Step Setup & Run Guide

### Step 1: Install Python Dependencies

```bash
cd /Users/shriram/Downloads/ETL
pip install -r requirements.txt
```

### Step 2: Install & Start MySQL

If MySQL is not installed:
```bash
# macOS (Homebrew)
brew install mysql
brew services start mysql

# Verify it's running
mysql -u root -p -e "SELECT VERSION();"
```

### Step 3: Configure .env

Edit `.env` with your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=YourPasswordHere
DB_NAME=healthcare_etl
LOG_LEVEL=INFO
```

### Step 4: Create the Database Schema

```bash
mysql -u root -p < db/schema.sql
```

Expected output:
```
+---------------------------------------------------+
| status                                            |
+---------------------------------------------------+
| ✅ Database healthcare_etl created successfully!   |
+---------------------------------------------------+

+----------------------------+
| Tables_in_healthcare_etl   |
+----------------------------+
| diagnoses                  |
| encounters                 |
| patients                   |
| pipeline_runs              |
+----------------------------+
```

### Step 5: Test Database Connection

```bash
PYTHONPATH=. python3 db/connection.py
```

Expected output:
```
==================================================
Healthcare ETL — Database Connection Test
==================================================
✅ Database connection successful!
   MySQL version : 8.0.xx
   Database      : healthcare_etl
   Tables (4)    : ['diagnoses', 'encounters', 'patients', 'pipeline_runs']
==================================================
```

### Step 6: Run the ETL Pipeline

```bash
PYTHONPATH=. python3 etl/pipeline.py
```

Expected output:
```
════════════════════════════════════════════════════════════
🚀 STARTING FULL ETL PIPELINE
════════════════════════════════════════════════════════════
EXTRACT ▸ Patients
   ✔ Extracted 10 rows × 11 columns
TRANSFORM ▸ Patients
   ✔ Cleaned and title-cased name columns
   ✔ Dropped 1 rows with critical missing values
   ✔ Removed 1 duplicate rows
   ✔ Standardized dates in 'date_of_birth'
   ✔ Standardized gender codes
   ✔ Masked PHI columns: ['ssn', 'phone']
   ✔ Computed age from 'date_of_birth'
   ✔ Assigned age groups: {'Middle-Aged': 5, 'Young Adult': 3}
   ✔ Patient transform complete → 8 clean rows
LOAD ▸ Patients
   🗑️  Truncated table 'patients'
   💾 Inserting 8 rows → 'patients'
   ✔ Inserted 8 rows into 'patients'
   🔍 Verified: 'patients' has 8 rows in database
...
🏁 PIPELINE COMPLETE
   ✅ Succeeded: 3  |  ❌ Failed: 0
════════════════════════════════════════════════════════════
```

### Step 7: Verify Data in MySQL

```bash
mysql -u root -p healthcare_etl
```

```sql
-- Check patients
SELECT patient_id, first_name, last_name, gender, age, age_group
FROM patients;

-- Check encounters with patient names
SELECT e.encounter_id, p.first_name, p.last_name,
       e.encounter_date, e.encounter_type
FROM encounters e
JOIN patients p ON e.patient_id = p.patient_id;

-- Check diagnoses with disease categories
SELECT d.icd_code, d.description, d.disease_category,
       d.severity, d.icd_valid
FROM diagnoses d;

-- Check pipeline run history
SELECT pipeline_name, status, rows_extracted,
       rows_transformed, rows_loaded, duration_seconds
FROM pipeline_runs;
```

### Step 8: Run Tests

```bash
# Unit tests (no MySQL needed)
PYTHONPATH=. python3 -m pytest tests/test_extract.py tests/test_transform.py -v

# All tests (requires MySQL)
PYTHONPATH=. python3 -m pytest tests/ -v
```

---

## 🗄️ Database Schema

```
patients (parent)
├── patient_id (PK)
├── first_name, last_name          → INDEX idx_patient_name
├── gender                         → INDEX idx_patient_gender
├── state                          → INDEX idx_patient_state
├── age_group                      → INDEX idx_patient_age_group
│
├── encounters (child, FK → patients)
│   ├── encounter_id (PK)
│   ├── patient_id (FK)            → INDEX idx_encounter_patient
│   ├── encounter_date             → INDEX idx_encounter_date
│   ├── encounter_type             → INDEX idx_encounter_type
│   │
│   └── diagnoses (child, FK → encounters)
│       ├── diagnosis_id (PK)
│       ├── encounter_id (FK)      → INDEX idx_diagnosis_encounter
│       ├── icd_code               → INDEX idx_diagnosis_icd
│       ├── disease_category       → INDEX idx_diagnosis_category
│       └── severity               → INDEX idx_diagnosis_severity
│
└── pipeline_runs (standalone audit table)
    ├── run_id (PK, auto-increment)
    ├── pipeline_name              → INDEX idx_run_name
    ├── status                     → INDEX idx_run_status
    └── completed_at               → INDEX idx_run_completed
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Data Processing | Pandas |
| Web Framework | FastAPI |
| Database | MySQL 8.0 + SQLAlchemy 2.0 |
| Config | Pydantic Settings + .env |
| Testing | pytest |
