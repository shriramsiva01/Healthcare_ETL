"""
pipeline.py — ETL Pipeline Orchestrator
=========================================
Ties Extract → Transform → Load together with:
  • Timing for each step and overall run
  • Row-count tracking (extracted / transformed / loaded)
  • Error handling and graceful failure per entity
  • Audit logging to the pipeline_runs table
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from config.settings import settings
from db.connection import get_engine

from etl.extract import extract_patients, extract_encounters, extract_diagnoses
from etl.transform import transform_patients, transform_encounters, transform_diagnoses
from etl.load import load_patients, load_encounters, load_diagnoses

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  Pipeline Result Dataclass
# ══════════════════════════════════════════════════════════════

@dataclass
class PipelineResult:
    """Stores the outcome of a single entity pipeline run."""
    pipeline_name: str
    status: str = "pending"
    rows_extracted: int = 0
    rows_transformed: int = 0
    rows_loaded: int = 0
    duration_seconds: float = 0.0
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def summary(self) -> str:
        """Human-readable one-line summary."""
        return (
            f"{self.pipeline_name}: {self.status} | "
            f"extracted={self.rows_extracted} → transformed={self.rows_transformed} "
            f"→ loaded={self.rows_loaded} | {self.duration_seconds}s"
        )


# ══════════════════════════════════════════════════════════════
#  ETL Pipeline Orchestrator
# ══════════════════════════════════════════════════════════════

class ETLPipeline:
    """
    Main orchestrator that runs Extract → Transform → Load
    for each healthcare entity (patients, encounters, diagnoses).
    """

    def __init__(self):
        self.engine = get_engine()
        self.raw_dir = settings.RAW_DATA_DIR

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
            format="%(asctime)s │ %(levelname)-8s │ %(message)s",
            datefmt="%H:%M:%S",
        )

    # ── Individual Entity Pipelines ──────────────────────────

    def run_patients(self) -> PipelineResult:
        """Run the full ETL pipeline for PATIENT data."""
        result = PipelineResult(pipeline_name="patients")
        start = time.time()

        try:
            # ── EXTRACT ──
            df_raw = extract_patients(self.raw_dir)
            result.rows_extracted = len(df_raw)

            # ── TRANSFORM ──
            df_clean = transform_patients(df_raw)
            result.rows_transformed = len(df_clean)

            # ── LOAD ──
            result.rows_loaded = load_patients(df_clean, self.engine)
            result.status = "success"

        except Exception as e:
            logger.exception("✖ Patient pipeline FAILED")
            result.status = "failed"
            result.error_message = str(e)

        result.duration_seconds = round(time.time() - start, 2)
        result.completed_at = datetime.now(timezone.utc)
        self._log_run(result)
        return result

    def run_encounters(self) -> PipelineResult:
        """Run the full ETL pipeline for ENCOUNTER data."""
        result = PipelineResult(pipeline_name="encounters")
        start = time.time()

        try:
            df_raw = extract_encounters(self.raw_dir)
            result.rows_extracted = len(df_raw)

            df_clean = transform_encounters(df_raw)
            result.rows_transformed = len(df_clean)

            result.rows_loaded = load_encounters(df_clean, self.engine)
            result.status = "success"

        except Exception as e:
            logger.exception("✖ Encounter pipeline FAILED")
            result.status = "failed"
            result.error_message = str(e)

        result.duration_seconds = round(time.time() - start, 2)
        result.completed_at = datetime.now(timezone.utc)
        self._log_run(result)
        return result

    def run_diagnoses(self) -> PipelineResult:
        """Run the full ETL pipeline for DIAGNOSIS data."""
        result = PipelineResult(pipeline_name="diagnoses")
        start = time.time()

        try:
            df_raw = extract_diagnoses(self.raw_dir)
            result.rows_extracted = len(df_raw)

            df_clean = transform_diagnoses(df_raw)
            result.rows_transformed = len(df_clean)

            result.rows_loaded = load_diagnoses(df_clean, self.engine)
            result.status = "success"

        except Exception as e:
            logger.exception("✖ Diagnosis pipeline FAILED")
            result.status = "failed"
            result.error_message = str(e)

        result.duration_seconds = round(time.time() - start, 2)
        result.completed_at = datetime.now(timezone.utc)
        self._log_run(result)
        return result

    # ── Full Pipeline Run ────────────────────────────────────

    def run(self) -> list[PipelineResult]:
        """
        Execute the complete ETL pipeline for ALL entities:
          1. Patients
          2. Encounters
          3. Diagnoses

        Each entity runs independently — a failure in one does NOT
        block the others.

        Returns:
            List of PipelineResult objects, one per entity.
        """
        logger.info("═" * 60)
        logger.info("🚀 STARTING FULL ETL PIPELINE")
        logger.info("═" * 60)

        overall_start = time.time()

        results = [
            self.run_patients(),
            self.run_encounters(),
            self.run_diagnoses(),
        ]

        overall_duration = round(time.time() - overall_start, 2)
        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")

        logger.info("═" * 60)
        logger.info("🏁 PIPELINE COMPLETE in %.2fs", overall_duration)
        logger.info("   ✅ Succeeded: %d  |  ❌ Failed: %d", success, failed)
        for r in results:
            logger.info("   %s", r.summary())
        logger.info("═" * 60)

        return results

    # ── Audit Logging to DB ──────────────────────────────────

    def _log_run(self, result: PipelineResult) -> None:
        """
        Persist pipeline run metadata to the `pipeline_runs` table
        for auditing and monitoring.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO pipeline_runs
                            (pipeline_name, status, rows_extracted,
                             rows_transformed, rows_loaded,
                             duration_seconds, error_message,
                             started_at, completed_at)
                        VALUES
                            (:name, :status, :extracted,
                             :transformed, :loaded,
                             :duration, :error,
                             :started, :completed)
                    """),
                    {
                        "name": result.pipeline_name,
                        "status": result.status,
                        "extracted": result.rows_extracted,
                        "transformed": result.rows_transformed,
                        "loaded": result.rows_loaded,
                        "duration": result.duration_seconds,
                        "error": result.error_message,
                        "started": result.started_at,
                        "completed": result.completed_at,
                    },
                )
            logger.info("   📝 Logged run to pipeline_runs table")
        except Exception:
            logger.warning(
                "   ⚠ Could not log pipeline run to DB "
                "(pipeline_runs table may not exist yet)"
            )


# ══════════════════════════════════════════════════════════════
#  CLI Entry Point
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pipeline = ETLPipeline()
    results = pipeline.run()

    print("\n" + "=" * 60)
    print("PIPELINE RESULTS SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r.summary()}")
    print("=" * 60)
