"""
connection.py — MySQL Database Connection Module
==================================================
Provides a singleton SQLAlchemy engine, session factory,
and database health-check utility.

All credentials are read from environment variables via
config/settings.py (backed by the .env file).

Connection URL format:
    mysql+pymysql://<user>:<password>@<host>:<port>/<database>
"""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


# ══════════════════════════════════════════════════════════════
#  Engine (singleton)
# ══════════════════════════════════════════════════════════════

def get_engine() -> Engine:
    """
    Return a singleton SQLAlchemy engine.

    Configuration:
        • pool_size=5       — keep 5 persistent connections
        • max_overflow=10   — allow up to 10 extra under load
        • pool_pre_ping=True — test connections before use
        • pool_recycle=3600  — recycle connections every hour
    """
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        logger.info("🔌 Creating database engine → %s@%s/%s",
                     settings.DB_USER, settings.DB_HOST, settings.DB_NAME)
        _engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
    return _engine


# ══════════════════════════════════════════════════════════════
#  Session Factory
# ══════════════════════════════════════════════════════════════

def get_session() -> Session:
    """Create and return a new database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def get_db():
    """
    FastAPI dependency — yields a DB session and auto-closes.

    Usage:
        @app.get("/endpoint")
        def handler(db: Session = Depends(get_db)):
            ...
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════
#  Health Check
# ══════════════════════════════════════════════════════════════

def check_connection() -> bool:
    """
    Test the database connection and print diagnostics.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Basic connectivity
            conn.execute(text("SELECT 1"))

            # Get MySQL version
            version = conn.execute(text("SELECT VERSION()")).scalar()

            # Get current database
            db_name = conn.execute(text("SELECT DATABASE()")).scalar()

            # Count tables
            tables = conn.execute(text("SHOW TABLES")).fetchall()
            table_names = [t[0] for t in tables]

        logger.info("✅ Database connection successful!")
        logger.info("   MySQL version : %s", version)
        logger.info("   Database      : %s", db_name)
        logger.info("   Tables (%d)   : %s", len(table_names), table_names)
        return True

    except Exception as e:
        logger.error("❌ Database connection FAILED: %s", str(e))
        logger.error("   Check your .env file:")
        logger.error("     DB_HOST=%s", settings.DB_HOST)
        logger.error("     DB_PORT=%s", settings.DB_PORT)
        logger.error("     DB_USER=%s", settings.DB_USER)
        logger.error("     DB_NAME=%s", settings.DB_NAME)
        return False


def create_tables() -> bool:
    """
    Create all tables using SQLAlchemy ORM models.
    This is an alternative to running schema.sql manually.

    Returns:
        True if tables were created successfully.
    """
    try:
        from db.models import Base
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created via ORM")
        return True
    except Exception as e:
        logger.error("❌ Failed to create tables: %s", str(e))
        return False


# ══════════════════════════════════════════════════════════════
#  CLI: Run directly to test connection
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 50)
    print("Healthcare ETL — Database Connection Test")
    print("=" * 50)
    success = check_connection()
    print("=" * 50)
    sys.exit(0 if success else 1)
