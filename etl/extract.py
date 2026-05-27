"""
extract.py — Data Extraction Module
=====================================
Reads raw healthcare data from CSV and JSON source files
into Pandas DataFrames for downstream transformation.

Supported sources:
  • CSV  → patients.csv, encounters.csv
  • JSON → diagnoses.json
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  CSV Extraction
# ──────────────────────────────────────────────────────────────

def extract_csv(filepath: str) -> pd.DataFrame:
    """
    Read a CSV file into a Pandas DataFrame.

    Args:
        filepath: Absolute or relative path to the CSV file.

    Returns:
        Raw DataFrame with all columns read as strings.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(filepath)
    if not path.exists():
        logger.error("CSV file not found: %s", filepath)
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    logger.info("📂 Extracting CSV: %s", path.name)
    df = pd.read_csv(filepath, dtype=str)
    logger.info("   ✔ Extracted %d rows × %d columns", len(df), len(df.columns))
    return df


# ──────────────────────────────────────────────────────────────
#  JSON Extraction
# ──────────────────────────────────────────────────────────────

def extract_json(filepath: str) -> pd.DataFrame:
    """
    Read a JSON file (array of objects) into a Pandas DataFrame.

    Args:
        filepath: Absolute or relative path to the JSON file.

    Returns:
        Raw DataFrame parsed from JSON array.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(filepath)
    if not path.exists():
        logger.error("JSON file not found: %s", filepath)
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    logger.info("📂 Extracting JSON: %s", path.name)
    df = pd.read_json(filepath)
    logger.info("   ✔ Extracted %d rows × %d columns", len(df), len(df.columns))
    return df


# ──────────────────────────────────────────────────────────────
#  High-level extraction functions (one per entity)
# ──────────────────────────────────────────────────────────────

def extract_patients(raw_dir: str) -> pd.DataFrame:
    """Extract patient records from patients.csv."""
    logger.info("━" * 50)
    logger.info("EXTRACT ▸ Patients")
    return extract_csv(str(Path(raw_dir) / "patients.csv"))


def extract_encounters(raw_dir: str) -> pd.DataFrame:
    """Extract encounter records from encounters.csv."""
    logger.info("━" * 50)
    logger.info("EXTRACT ▸ Encounters")
    return extract_csv(str(Path(raw_dir) / "encounters.csv"))


def extract_diagnoses(raw_dir: str) -> pd.DataFrame:
    """Extract diagnosis records from diagnoses.json."""
    logger.info("━" * 50)
    logger.info("EXTRACT ▸ Diagnoses")
    return extract_json(str(Path(raw_dir) / "diagnoses.json"))
