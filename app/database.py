"""
Smart Complaint Management System
SQLAlchemy database engine, session management, and declarative base.
"""
# imort standard libraries
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use (handles MySQL timeouts)
    pool_recycle=3600,    # Recycle connections every hour
)

# ---------------------------------------------------------------------------
# MySQL UTF-8 Configuration
# ---------------------------------------------------------------------------   

@event.listens_for(engine, "connect")
def _set_mysql_charset(dbapi_connection, connection_record):
    """Ensure every new connection uses utf8mb4."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Dependency for FastAPI
# ---------------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency that yields a database session.
    Automatically commits on success and rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialization helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all tables defined by ORM models.
    Called during application startup (before Alembic is set up).
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")


# ---------------------------------------------------------------------------
# Database Connectivity Check
# ---------------------------------------------------------------------------


def check_db_connection() -> bool:
    """Test database connectivity. Returns True if successful."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.") 
        return True
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        return False
