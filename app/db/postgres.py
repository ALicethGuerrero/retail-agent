"""Conexión y migración de base de datos PostgreSQL utilizando SQLAlchemy."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

load_dotenv()


def use_mock_data() -> bool:
    """Indicar si el repositorio debe usar datos locales en memoria."""
    return os.getenv("USE_MOCK_DATA", "false").lower() == "true"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Crear un engine PostgreSQL a partir de DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Configura DATABASE_URL para usar PostgreSQL.")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    url = make_url(database_url).difference_update_query(["pgbouncer"])
    options = {"pool_pre_ping": True}
    if url.port == 6543:
        options["poolclass"] = NullPool
    return create_engine(url, **options)


def init_db() -> None:
    """Aplicar, en orden, los scripts SQL de supabase/migrations."""
    migrations_dir = Path(__file__).parents[2] / "supabase" / "migrations"
    migrations = sorted(migrations_dir.glob("*.sql"))
    if not migrations:
        raise RuntimeError(f"No hay migraciones en {migrations_dir}.")

    engine = get_engine()
    try:
        with engine.begin() as connection:
            for migration in migrations:
                script = migration.read_text(encoding="utf-8")
                connection.exec_driver_sql(script.replace("%", "%%"))
    finally:
        engine.dispose()