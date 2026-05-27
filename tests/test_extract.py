"""
Tests for the ETL extract module.
"""

import json
import pandas as pd
import pytest
from etl.extract import extract_csv, extract_json


class TestExtractCSV:
    """Tests for CSV extraction."""

    def test_extract_valid_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,age\n1,Alice,30\n2,Bob,25\n")
        df = extract_csv(str(csv_file))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name", "age"]

    def test_extract_csv_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_csv("/nonexistent/path/data.csv")

    def test_extract_csv_reads_as_string(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,value\n1,100\n2,200\n")
        df = extract_csv(str(csv_file))
        # Pandas 3.0+ uses StringDtype; older uses object
        assert "str" in str(df["id"].dtype).lower() or df["id"].dtype == object


class TestExtractJSON:
    """Tests for JSON extraction."""

    def test_extract_valid_json(self, tmp_path):
        json_file = tmp_path / "test.json"
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        json_file.write_text(json.dumps(data))
        df = extract_json(str(json_file))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_extract_json_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_json("/nonexistent/path/data.json")
