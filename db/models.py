"""
SQLAlchemy ORM models for the Healthcare ETL warehouse.

These models mirror the tables defined in db/schema.sql
and can be used to create tables via:
    from db.models import Base
    Base.metadata.create_all(bind=engine)
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass


class Patient(Base):
    __tablename__ = "patients"

    patient_id    = Column(Integer, primary_key=True)
    first_name    = Column(String(100), nullable=False)
    last_name     = Column(String(100), nullable=False)
    date_of_birth = Column(String(10))
    gender        = Column(String(10))
    phone_masked  = Column(String(64))
    ssn_masked    = Column(String(64))
    address       = Column(String(255))
    city          = Column(String(100))
    state         = Column(String(50))
    zip           = Column(String(10))
    age           = Column(Integer)
    age_group     = Column(String(20))
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_patient_name", "last_name", "first_name"),
        Index("idx_patient_state", "state"),
        Index("idx_patient_age_group", "age_group"),
        Index("idx_patient_gender", "gender"),
    )

    def __repr__(self):
        return f"<Patient {self.patient_id}: {self.first_name} {self.last_name}>"


class Encounter(Base):
    __tablename__ = "encounters"

    encounter_id   = Column(Integer, primary_key=True)
    patient_id     = Column(Integer, ForeignKey("patients.patient_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    encounter_date = Column(String(10))
    encounter_type = Column(String(50))
    provider_name  = Column(String(150))
    facility       = Column(String(200))
    created_at     = Column(DateTime, server_default=func.now())

    # Relationships
    patient   = relationship("Patient", back_populates="encounters")
    diagnoses = relationship("Diagnosis", back_populates="encounter", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_encounter_patient", "patient_id"),
        Index("idx_encounter_date", "encounter_date"),
        Index("idx_encounter_type", "encounter_type"),
    )

    def __repr__(self):
        return f"<Encounter {self.encounter_id} for Patient {self.patient_id}>"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    diagnosis_id     = Column(Integer, primary_key=True)
    encounter_id     = Column(Integer, ForeignKey("encounters.encounter_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    icd_code         = Column(String(10))
    description      = Column(String(255))
    severity         = Column(String(20))
    icd_valid        = Column(Boolean, default=True)
    disease_category = Column(String(50))
    created_at       = Column(DateTime, server_default=func.now())

    # Relationships
    encounter = relationship("Encounter", back_populates="diagnoses")

    # Indexes
    __table_args__ = (
        Index("idx_diagnosis_encounter", "encounter_id"),
        Index("idx_diagnosis_icd", "icd_code"),
        Index("idx_diagnosis_category", "disease_category"),
        Index("idx_diagnosis_severity", "severity"),
    )

    def __repr__(self):
        return f"<Diagnosis {self.diagnosis_id}: {self.icd_code}>"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id           = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_name    = Column(String(50), nullable=False)
    status           = Column(String(20), nullable=False)
    rows_extracted   = Column(Integer, default=0)
    rows_transformed = Column(Integer, default=0)
    rows_loaded      = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    error_message    = Column(Text)
    started_at       = Column(DateTime)
    completed_at     = Column(DateTime)

    # Indexes
    __table_args__ = (
        Index("idx_run_name", "pipeline_name"),
        Index("idx_run_status", "status"),
        Index("idx_run_completed", "completed_at"),
    )

    def __repr__(self):
        return f"<PipelineRun {self.run_id}: {self.pipeline_name} [{self.status}]>"
