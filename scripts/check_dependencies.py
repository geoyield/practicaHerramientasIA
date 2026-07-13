"""Comprueba que las dependencias esenciales están disponibles."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

REQUIRED_MODULES = (
    ("fastapi", "fastapi"),
    ("starlette", "starlette"),
    ("sqlalchemy", "sqlalchemy"),
    ("jinja2", "jinja2"),
    ("psycopg", "psycopg"),
    ("uvicorn", "uvicorn"),
)


def main() -> None:
    errors: list[str] = []
    detected: list[str] = []

    for module_name, package_name in REQUIRED_MODULES:
        try:
            import_module(module_name)
            detected.append(f"{package_name}={version(package_name)}")
        except (ImportError, PackageNotFoundError) as exc:
            errors.append(f"{package_name}: {exc}")

    if errors:
        joined = "\n - ".join(errors)
        raise SystemExit(f"Dependencias ausentes o dañadas:\n - {joined}")

    print("Dependencias verificadas: " + ", ".join(detected))


if __name__ == "__main__":
    main()
