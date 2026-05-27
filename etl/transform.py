"""
transform.py — Data Transformation Module
==========================================
Cleans, validates, and enriches raw healthcare DataFrames.

Capabilities:
  • Handle missing values (drop / fill)
  • Remove duplicate records
  • Normalize column names (lowercase, underscored)
  • Standardize dates to YYYY-MM-DD
  • Standardize gender codes → Male / Female / Other
  • Mask PHI fields (HIPAA — SHA-256 hashing)
  • Validate ICD-10 codes
  • NEW FEATURES:
      – Compute patient age and age_group
      – Derive disease_category from ICD-10 code prefix
"""

import hashlib
import logging
import re
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

# ICD-10 format: letter + 2 digits, optional dot + up to 4 alphanumeric
ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?[A-Z]?$", re.IGNORECASE)

# ── ICD-10 chapter mapping (first letter → disease category) ─
ICD10_CATEGORIES = {
    "A": "Infectious Diseases",
    "B": "Infectious Diseases",
    "C": "Neoplasms",
    "D": "Blood Diseases",
    "E": "Endocrine/Metabolic",
    "F": "Mental Disorders",
    "G": "Nervous System",
    "H": "Eye/Ear Diseases",
    "I": "Circulatory System",
    "J": "Respiratory System",
    "K": "Digestive System",
    "L": "Skin Diseases",
    "M": "Musculoskeletal",
    "N": "Genitourinary",
    "O": "Pregnancy/Childbirth",
    "P": "Perinatal Conditions",
    "Q": "Congenital Malformations",
    "R": "Symptoms/Abnormal Findings",
    "S": "Injury/Trauma",
    "T": "Injury/Poisoning",
    "U": "Special Codes",
    "V": "External Causes",
    "W": "External Causes",
    "X": "External Causes",
    "Y": "External Causes",
    "Z": "Health Services Factors",
}


# ══════════════════════════════════════════════════════════════
#  SHARED TRANSFORMS
# ══════════════════════════════════════════════════════════════

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize all column names:
      • lowercase
      • replace spaces / hyphens with underscores
      • strip leading/trailing whitespace
    """
    original = list(df.columns)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
    )
    renamed = {o: n for o, n in zip(original, df.columns) if o != n}
    if renamed:
        logger.info("   ✔ Normalized columns: %s", renamed)
    else:
        logger.info("   ✔ Column names already normalized")
    return df


def handle_missing_values(
    df: pd.DataFrame,
    drop_subset: list[str] | None = None,
    fill_map: dict[str, object] | None = None,
) -> pd.DataFrame:
    """
    Handle missing values in a DataFrame.

    Args:
        df: Input DataFrame.
        drop_subset: If set, drop rows where ALL of these columns are null.
        fill_map: Dict of {column: fill_value} for targeted filling.

    Returns:
        DataFrame with missing values handled.
    """
    initial = len(df)

    # Drop rows where critical fields are entirely null
    if drop_subset:
        df = df.dropna(subset=drop_subset, how="all")

    # Fill specific columns with defaults
    if fill_map:
        for col, value in fill_map.items():
            if col in df.columns:
                df[col] = df[col].fillna(value)

    removed = initial - len(df)
    if removed:
        logger.info("   ✔ Dropped %d rows with critical missing values", removed)
    else:
        logger.info("   ✔ No rows dropped for missing values")
    return df


def remove_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str = "first",
) -> pd.DataFrame:
    """
    Remove duplicate rows.

    Args:
        df: Input DataFrame.
        subset: Columns to consider for identifying duplicates.
        keep: Which occurrence to keep ('first', 'last', False).

    Returns:
        De-duplicated DataFrame.
    """
    initial = len(df)
    df = df.drop_duplicates(subset=subset, keep=keep)
    removed = initial - len(df)
    if removed:
        logger.info("   ✔ Removed %d duplicate rows", removed)
    else:
        logger.info("   ✔ No duplicates found")
    return df.reset_index(drop=True)


def standardize_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Parse varied date formats → YYYY-MM-DD string.

    Handles formats like:
      • 1985-03-15, 03/15/1985, 15-Mar-1985, 1995/11/30
    """
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
        df[col] = df[col].dt.strftime("%Y-%m-%d")
        nulls = df[col].isna().sum()
        if nulls:
            logger.warning("   ⚠ %d unparseable dates in '%s'", nulls, col)
        else:
            logger.info("   ✔ Standardized dates in '%s'", col)
    return df


# ══════════════════════════════════════════════════════════════
#  PATIENT TRANSFORMS
# ══════════════════════════════════════════════════════════════

def clean_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize first_name and last_name to Title Case."""
    for col in ("first_name", "last_name"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace({"Nan": None, "None": None, "": None})
    logger.info("   ✔ Cleaned and title-cased name columns")
    return df


def map_gender_codes(df: pd.DataFrame, col: str = "gender") -> pd.DataFrame:
    """Standardize gender values → Male / Female / Other."""
    if col not in df.columns:
        return df

    mapping = {
        "m": "Male", "male": "Male",
        "f": "Female", "female": "Female",
    }
    df[col] = (
        df[col].astype(str).str.strip().str.lower()
        .map(mapping).fillna("Other")
    )
    logger.info("   ✔ Standardized gender codes")
    return df


def mask_phi(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Mask Protected Health Information via SHA-256 hashing.
    Produces a 16-char hex digest for each value.
    """
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(
            lambda v: hashlib.sha256(str(v).encode()).hexdigest()[:16]
            if pd.notna(v) and str(v).strip() not in ("", "nan", "None")
            else None
        )
    logger.info("   ✔ Masked PHI columns: %s", cols)
    return df


def compute_age(df: pd.DataFrame, dob_col: str = "date_of_birth") -> pd.DataFrame:
    """
    Compute patient age from date_of_birth (YYYY-MM-DD string).
    Adds 'age' column as integer years.
    """
    if dob_col not in df.columns:
        return df

    today = date.today()

    def _calc_age(dob_str):
        try:
            parts = str(dob_str).split("-")
            born = date(int(parts[0]), int(parts[1]), int(parts[2]))
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
            )
        except (ValueError, IndexError, TypeError):
            return None

    df["age"] = df[dob_col].apply(_calc_age)
    logger.info("   ✔ Computed age from '%s'", dob_col)
    return df


def assign_age_group(df: pd.DataFrame, age_col: str = "age") -> pd.DataFrame:
    """
    Assign age_group based on computed age:
      0-17   → Pediatric
      18-39  → Young Adult
      40-64  → Middle-Aged
      65+    → Senior
    """
    if age_col not in df.columns:
        return df

    bins = [0, 17, 39, 64, 120]
    labels = ["Pediatric", "Young Adult", "Middle-Aged", "Senior"]

    # Convert to numeric, coerce errors
    ages = pd.to_numeric(df[age_col], errors="coerce")
    age_groups = pd.cut(ages, bins=bins, labels=labels, right=True)
    # Add "Unknown" as a valid category before filling NaN
    age_groups = age_groups.cat.add_categories("Unknown")
    df["age_group"] = age_groups.fillna("Unknown").astype(str)

    logger.info("   ✔ Assigned age groups: %s", df["age_group"].value_counts().to_dict())
    return df


def transform_patients(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full patient transformation pipeline:
      1. Normalize column names
      2. Clean names (Title Case)
      3. Handle missing values
      4. Remove duplicates (name + DOB)
      5. Standardize dates
      6. Standardize gender
      7. Mask PHI (SSN, phone)
      8. Compute age + age_group
    """
    logger.info("━" * 50)
    logger.info("TRANSFORM ▸ Patients")

    df = normalize_column_names(df)
    df = clean_names(df)
    df = handle_missing_values(df, drop_subset=["first_name", "last_name"])
    df = remove_duplicates(df, subset=["first_name", "last_name", "date_of_birth"])
    df = standardize_dates(df, ["date_of_birth"])
    df = map_gender_codes(df)
    df = mask_phi(df, ["ssn", "phone"])
    df = compute_age(df)
    df = assign_age_group(df)

    # Rename masked columns for clarity
    df = df.rename(columns={"ssn": "ssn_masked", "phone": "phone_masked"})

    logger.info("   ✔ Patient transform complete → %d clean rows", len(df))
    return df


# ══════════════════════════════════════════════════════════════
#  ENCOUNTER TRANSFORMS
# ══════════════════════════════════════════════════════════════

def transform_encounters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full encounter transformation pipeline:
      1. Normalize column names
      2. Handle missing values (drop if patient_id missing)
      3. Remove duplicates
      4. Standardize dates
      5. Title-case encounter_type
    """
    logger.info("━" * 50)
    logger.info("TRANSFORM ▸ Encounters")

    df = normalize_column_names(df)
    df = handle_missing_values(df, drop_subset=["patient_id"])
    df = remove_duplicates(df, subset=["encounter_id"])
    df = standardize_dates(df, ["encounter_date"])

    if "encounter_type" in df.columns:
        df["encounter_type"] = df["encounter_type"].astype(str).str.strip().str.title()
        logger.info("   ✔ Title-cased encounter_type")

    logger.info("   ✔ Encounter transform complete → %d clean rows", len(df))
    return df


# ══════════════════════════════════════════════════════════════
#  DIAGNOSIS TRANSFORMS
# ══════════════════════════════════════════════════════════════

def validate_icd_codes(df: pd.DataFrame, col: str = "icd_code") -> pd.DataFrame:
    """
    Validate ICD-10 codes against the standard format.
    Adds 'icd_valid' boolean column.
    """
    if col not in df.columns:
        return df

    df["icd_valid"] = df[col].apply(
        lambda code: bool(ICD10_PATTERN.match(str(code))) if pd.notna(code) else False
    )
    invalid = (~df["icd_valid"]).sum()
    if invalid:
        logger.warning("   ⚠ %d invalid ICD-10 codes found", invalid)
    else:
        logger.info("   ✔ All ICD-10 codes valid")
    return df


def assign_disease_category(df: pd.DataFrame, col: str = "icd_code") -> pd.DataFrame:
    """
    Derive disease_category from the first letter of the ICD-10 code.

    Mapping follows the ICD-10 chapter structure:
      A/B → Infectious Diseases,  C → Neoplasms,  E → Endocrine, etc.
    """
    if col not in df.columns:
        return df

    def _categorize(code):
        if pd.isna(code) or not str(code).strip():
            return "Unknown"
        first_char = str(code).strip()[0].upper()
        return ICD10_CATEGORIES.get(first_char, "Unknown")

    df["disease_category"] = df[col].apply(_categorize)
    logger.info(
        "   ✔ Assigned disease categories: %s",
        df["disease_category"].value_counts().to_dict(),
    )
    return df


def transform_diagnoses(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full diagnosis transformation pipeline:
      1. Normalize column names
      2. Handle missing values
      3. Remove duplicates
      4. Validate ICD-10 codes
      5. Assign disease category
    """
    logger.info("━" * 50)
    logger.info("TRANSFORM ▸ Diagnoses")

    df = normalize_column_names(df)
    df = handle_missing_values(df, drop_subset=["encounter_id"])
    df = remove_duplicates(df, subset=["diagnosis_id"])
    df = validate_icd_codes(df)
    df = assign_disease_category(df)

    logger.info("   ✔ Diagnosis transform complete → %d clean rows", len(df))
    return df
