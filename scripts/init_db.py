"""Create the database schema directly from the SQLAlchemy models.

This bootstrap is intentionally independent of Alembic/Mako so the demo can be
installed in restricted or offline package environments. For production,
introduce a migration tool once the dependency mirror is available.
"""

from database import engine
from models import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Esquema de PostgreSQL verificado/creado correctamente.")


if __name__ == "__main__":
    main()
