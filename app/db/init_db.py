"""Script de CLI para aplicar migraciones e inicializar la base de datos SQL."""

from sqlalchemy.exc import OperationalError

from app.db.postgres import init_db


def main() -> int:
    """Ejecutar las migraciones SQL en orden e informar el resultado."""
    try:
        init_db()
    except OperationalError as error:
        if "password authentication failed" in str(error):
            raise RuntimeError(
                "PostgreSQL rechazó la contraseña. Usa la contraseña de base de "
                "datos de Supabase en DATABASE_URL; no uses SUPABASE_KEY ni la "
                "clave anon."
            ) from error
        raise
    print("Base de datos inicializada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())