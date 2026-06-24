"""
Alembic environment configuration.
Connects Alembic to our application's SQLAlchemy models and database settings.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Import our app's Base and all models ──────────────────────────────────
from app.config import get_settings
from app.database import Base

# Import all models so Base.metadata is fully populated
from app.models import (  # noqa: F401
    Complaint,
    Department,
    Feedback,
    User,
)

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Set the SQLAlchemy URL from our app settings
# Escape '%' for configparser (passwords may contain URL-encoded special chars)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects to the database and applies migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
