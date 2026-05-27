"""
Tests for the ETL transform module.
"""

import pandas as pd
import pytest

from etl.transform import (
    normalize_column_names,
    handle_missing_values,
    remove_duplicates,
    standardize_dates,
    clean_names,
    map_gender_codes,
    mask_phi,
    compute_age,
    assign_age_group,
    validate_icd_codes,
    assign_disease_category,
    transform_patients,
    transform_encounters,
    transform_diagnoses,
)


# ══════════════════════════════════════════════════════════════
#  Shared Transforms
# ══════════════════════════════════════════════════════════════

class TestNormalizeColumnNames:
    def test_lowercases_and_underscores(self):
        df = pd.DataFrame({"First Name": [1], "Date-Of-Birth": [2], "  ZIP ": [3]})
        result = normalize_column_names(df)
        assert list(result.columns) == ["first_name", "date_of_birth", "zip"]


class TestHandleMissingValues:
    def test_drops_rows_with_all_null_subset(self):
        df = pd.DataFrame({"a": ["x", None, "z"], "b": ["y", None, None]})
        result = handle_missing_values(df, drop_subset=["a", "b"])
        assert len(result) == 2  # second row has both null

    def test_fills_specific_columns(self):
        df = pd.DataFrame({"a": [1, None], "b": [None, 2]})
        result = handle_missing_values(df, fill_map={"a": 0, "b": 99})
        assert result.iloc[1]["a"] == 0
        assert result.iloc[0]["b"] == 99


class TestRemoveDuplicates:
    def test_removes_exact_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        result = remove_duplicates(df, subset=["a", "b"])
        assert len(result) == 2

    def test_keeps_first_by_default(self):
        df = pd.DataFrame({"a": [1, 1], "b": ["first", "second"]})
        result = remove_duplicates(df, subset=["a"])
        assert result.iloc[0]["b"] == "first"


class TestStandardizeDates:
    def test_various_formats(self):
        df = pd.DataFrame({"dob": ["1985-03-15", "03/15/1985", "15-Mar-1985"]})
        result = standardize_dates(df, ["dob"])
        for val in result["dob"]:
            assert val == "1985-03-15"

    def test_invalid_dates_become_null(self):
        df = pd.DataFrame({"dob": ["not-a-date"]})
        result = standardize_dates(df, ["dob"])
        assert pd.isna(result.iloc[0]["dob"])


# ══════════════════════════════════════════════════════════════
#  Patient Transforms
# ══════════════════════════════════════════════════════════════

class TestCleanNames:
    def test_title_cases_names(self):
        df = pd.DataFrame({"first_name": ["john"], "last_name": ["DOE"]})
        result = clean_names(df)
        assert result.iloc[0]["first_name"] == "John"
        assert result.iloc[0]["last_name"] == "Doe"


class TestMapGenderCodes:
    def test_maps_all_variants(self):
        df = pd.DataFrame({"gender": ["M", "f", "Female", "MALE", "unknown"]})
        result = map_gender_codes(df)
        expected = ["Male", "Female", "Female", "Male", "Other"]
        assert list(result["gender"]) == expected


class TestMaskPHI:
    def test_masks_ssn(self):
        df = pd.DataFrame({"ssn": ["123-45-6789"]})
        result = mask_phi(df, ["ssn"])
        assert result.iloc[0]["ssn"] != "123-45-6789"
        assert len(result.iloc[0]["ssn"]) == 16

    def test_null_stays_null(self):
        df = pd.DataFrame({"ssn": [None]})
        result = mask_phi(df, ["ssn"])
        assert result.iloc[0]["ssn"] is None


class TestComputeAge:
    def test_computes_valid_age(self):
        df = pd.DataFrame({"date_of_birth": ["1990-01-01"]})
        result = compute_age(df)
        assert "age" in result.columns
        assert result.iloc[0]["age"] >= 35  # born 1990, test will pass for years

    def test_invalid_dob_returns_none(self):
        df = pd.DataFrame({"date_of_birth": ["invalid"]})
        result = compute_age(df)
        assert result.iloc[0]["age"] is None


class TestAssignAgeGroup:
    def test_correct_buckets(self):
        df = pd.DataFrame({"age": [5, 25, 50, 70, None]})
        result = assign_age_group(df)
        assert result.iloc[0]["age_group"] == "Pediatric"
        assert result.iloc[1]["age_group"] == "Young Adult"
        assert result.iloc[2]["age_group"] == "Middle-Aged"
        assert result.iloc[3]["age_group"] == "Senior"
        assert result.iloc[4]["age_group"] == "Unknown"


# ══════════════════════════════════════════════════════════════
#  Diagnosis Transforms
# ══════════════════════════════════════════════════════════════

class TestValidateICDCodes:
    def test_valid_codes(self):
        df = pd.DataFrame({"icd_code": ["J06.9", "E11.9", "I21.0"]})
        result = validate_icd_codes(df)
        assert result["icd_valid"].all()

    def test_invalid_codes(self):
        df = pd.DataFrame({"icd_code": ["INVALID", "123", ""]})
        result = validate_icd_codes(df)
        assert not result["icd_valid"].any()


class TestAssignDiseaseCategory:
    def test_correct_categories(self):
        df = pd.DataFrame({"icd_code": ["J06.9", "I21.0", "E11.9", "INVALID"]})
        result = assign_disease_category(df)
        assert result.iloc[0]["disease_category"] == "Respiratory System"
        assert result.iloc[1]["disease_category"] == "Circulatory System"
        assert result.iloc[2]["disease_category"] == "Endocrine/Metabolic"
        assert result.iloc[3]["disease_category"] == "Circulatory System"  # I from INVALID

    def test_null_code_returns_unknown(self):
        df = pd.DataFrame({"icd_code": [None]})
        result = assign_disease_category(df)
        assert result.iloc[0]["disease_category"] == "Unknown"


# ══════════════════════════════════════════════════════════════
#  Full Transform Pipelines
# ══════════════════════════════════════════════════════════════

class TestTransformPatients:
    def test_full_pipeline_outputs_expected_columns(self):
        df = pd.DataFrame({
            "patient_id": ["1", "2"],
            "first_name": ["alice", "BOB"],
            "last_name": ["smith", "JONES"],
            "date_of_birth": ["1990-05-10", "1985-12-25"],
            "gender": ["f", "M"],
            "phone": ["555-1234", "555-5678"],
            "ssn": ["111-22-3333", "444-55-6666"],
        })
        result = transform_patients(df)
        assert "age" in result.columns
        assert "age_group" in result.columns
        assert "ssn_masked" in result.columns
        assert "phone_masked" in result.columns
        assert result.iloc[0]["first_name"] == "Alice"
        assert result.iloc[0]["gender"] == "Female"


class TestTransformEncounters:
    def test_full_pipeline(self):
        df = pd.DataFrame({
            "encounter_id": ["1001", "1002"],
            "patient_id": ["1", "2"],
            "encounter_date": ["2024-01-15", "01/18/2024"],
            "encounter_type": ["outpatient", "emergency"],
        })
        result = transform_encounters(df)
        assert len(result) == 2
        assert result.iloc[0]["encounter_type"] == "Outpatient"


class TestTransformDiagnoses:
    def test_full_pipeline(self):
        df = pd.DataFrame({
            "diagnosis_id": [1, 2],
            "encounter_id": [1001, 1002],
            "icd_code": ["J06.9", "INVALID"],
            "description": ["Cold", "Bad code"],
            "severity": ["Mild", "Unknown"],
        })
        result = transform_diagnoses(df)
        assert "icd_valid" in result.columns
        assert "disease_category" in result.columns
        assert result.iloc[0]["disease_category"] == "Respiratory System"
