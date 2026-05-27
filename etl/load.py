"""
load.py — Data Loading Module
===============================
Inserts cleaned Pandas DataFrames into MySQL tables.

Two loading strategies:
  1. TRUNCATE + INSERT  (default) — clears existing data, inserts fresh
  2. APPEND             — adds new rows to existing data

Each entity loader:
  • Selects only the columns that match the target table
  • Handles type conversions (e.g., boolean → int for MySQL)
  • Verifies row count after loading
  • Logs every step with timing
"""

import logging
import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  CORE LOADING FUNCTIONS
# ══════════════════════════════════════════════════════════════

def truncate_table(table_name: str, engine: Engine) -> None:
    """
    Safely truncate a table, temporarily disabling FK checks.
    This allows loading parent tables after children are cleared.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.execute(text(f"TRUNCATE TABLE `{table_name}`"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        logger.info("   🗑️  Truncated table '%s'", table_name)
    except Exception as e:
        logger.error("   ✖ Failed to truncate '%s': %s", table_name, e)
        raise


def insert_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
) -> int:
    """
    Insert a DataFrame into an existing MySQL table using
    pandas to_sql with 'append' mode.

    This does NOT drop/recreate the table, preserving indexes
    and foreign key constraints defined in schema.sql.

    Args:
        df: Cleaned DataFrame ready for insertion.
        table_name: Target table name in MySQL.
        engine: SQLAlchemy engine instance.

    Returns:
        Number of rows inserted.
    """
    rows = len(df)
    if rows == 0:
        logger.warning("   ⚠ No rows to insert into '%s'", table_name)
        return 0

    start = time.time()
    logger.info("   💾 Inserting %d rows → '%s'", rows, table_name)

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",   # append to existing table (preserves schema)
            index=False,
            method="multi",       # batch INSERT for performance
            chunksize=500,        # 500 rows per INSERT statement
        )
        elapsed = round(time.time() - start, 2)
        logger.info("   ✔ Inserted %d rows into '%s' (%.2fs)", rows, table_name, elapsed)
        return rows

    except Exception as e:
        logger.error("   ✖ Failed to insert into '%s': %s", table_name, str(e))
        raise


def verify_row_count(table_name: str, engine: Engine) -> int:
    """
    Query actual row count from MySQL after loading.

    Returns:
        Row count, or -1 if query fails.
    """
    try:
        with engine.connect() as conn:
            count = conn.execute(
                text(f"SELECT COUNT(*) FROM `{table_name}`")
            ).scalar()
        logger.info("   🔍 Verified: '%s' has %d rows in database", table_name, count)
        return count
    except Exception as e:
        logger.warning("   ⚠ Could not verify '%s': %s", table_name, e)
        return -1


# ══════════════════════════════════════════════════════════════
#  PER-ENTITY LOADING FUNCTIONS
# ══════════════════════════════════════════════════════════════

def load_patients(df: pd.DataFrame, engine: Engine) -> int:
    """
    Load cleaned patient data into the `patients` table.

    Steps:
      1. Select columns matching the patients schema
      2. Convert data types for MySQL compatibility
      3. Truncate existing data
      4. Insert fresh data
      5. Verify row count

    Target columns:
        patient_id, first_name, last_name, date_of_birth, gender,
        phone_masked, ssn_masked, address, city, state, zip, age, age_group
    """
    logger.info("━" * 50)
    logger.info("LOAD ▸ Patients")

    # Column selection — only include columns that exist in the DataFrame
    target_cols = [
        "patient_id", "first_name", "last_name", "date_of_birth",
        "gender", "phone_masked", "ssn_masked", "address",
        "city", "state", "zip", "age", "age_group",
    ]
    cols = [c for c in target_cols if c in df.columns]
    load_df = df[cols].copy()

    # Type conversions
    if "patient_id" in load_df.columns:
        load_df["patient_id"] = pd.to_numeric(load_df["patient_id"], errors="coerce").astype("Int64")
    if "age" in load_df.columns:
        load_df["age"] = pd.to_numeric(load_df["age"], errors="coerce").astype("Int64")

    # Truncate → Insert → Verify
    truncate_table("patients", engine)
    rows = insert_dataframe(load_df, "patients", engine)
    verify_row_count("patients", engine)
    return rows


def load_encounters(df: pd.DataFrame, engine: Engine) -> int:
    """
    Load cleaned encounter data into the `encounters` table.

    Target columns:
        encounter_id, patient_id, encounter_date,
        encounter_type, provider_name, facility
    """
    logger.info("━" * 50)
    logger.info("LOAD ▸ Encounters")

    target_cols = [
        "encounter_id", "patient_id", "encounter_date",
        "encounter_type", "provider_name", "facility",
    ]
    cols = [c for c in target_cols if c in df.columns]
    load_df = df[cols].copy()

    # Type conversions
    for int_col in ("encounter_id", "patient_id"):
        if int_col in load_df.columns:
            load_df[int_col] = pd.to_numeric(load_df[int_col], errors="coerce").astype("Int64")

    # Truncate → Insert → Verify
    truncate_table("encounters", engine)
    rows = insert_dataframe(load_df, "encounters", engine)
    verify_row_count("encounters", engine)
    return rows


def load_diagnoses(df: pd.DataFrame, engine: Engine) -> int:
    """
    Load cleaned diagnosis data into the `diagnoses` table.

    Target columns:
        diagnosis_id, encounter_id, icd_code, description,
        severity, icd_valid, disease_category
    """
    logger.info("━" * 50)
    logger.info("LOAD ▸ Diagnoses")

    target_cols = [
        "diagnosis_id", "encounter_id", "icd_code", "description",
        "severity", "icd_valid", "disease_category",
    ]
    cols = [c for c in target_cols if c in df.columns]
    load_df = df[cols].copy()

    # Type conversions
    for int_col in ("diagnosis_id", "encounter_id"):
        if int_col in load_df.columns:
            load_df[int_col] = pd.to_numeric(load_df[int_col], errors="coerce").astype("Int64")
    # Convert boolean icd_valid → int (MySQL BOOLEAN = TINYINT)
    if "icd_valid" in load_df.columns:
        load_df["icd_valid"] = load_df["icd_valid"].astype(int)

    # Truncate → Insert → Verify
    truncate_table("diagnoses", engine)
    rows = insert_dataframe(load_df, "diagnoses", engine)
    verify_row_count("diagnoses", engine)
    return rows
