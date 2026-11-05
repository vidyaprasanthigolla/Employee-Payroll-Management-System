import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("payroll.db")
logging.basicConfig(level=logging.INFO)

Base = declarative_base()


def get_engine():
    """
    Initializes SQLAlchemy database engine.
    Tries primary MySQL database first; if unavailable and fallback is enabled,
    safely falls back to local SQLite for frictionless local development.
    """
    db_url = settings.DATABASE_URL
    try:
        if db_url.startswith("mysql"):
            # Try connecting with short pool timeout to verify MySQL connectivity
            eng = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 3}
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to primary MySQL database.")
            return eng
        else:
            return create_engine(
                db_url,
                connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
            )
    except Exception as e:
        if settings.USE_SQLITE_FALLBACK:
            logger.warning(
                f"Primary MySQL connection failed ({e}). "
                f"Falling back gracefully to SQLite: {settings.SQLITE_FALLBACK_URL}"
            )
            return create_engine(
                settings.SQLITE_FALLBACK_URL,
                connect_args={"check_same_thread": False}
            )
        raise e


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """FastAPI dependency yielding database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
