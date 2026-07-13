# Ponte Cachas · PostgreSQL + SQLAlchemy

Portal persistente construido con **FastAPI, SQLAlchemy 2, PostgreSQL, Jinja2, CSS y JavaScript**.

Esta revisión corrige dos problemas de instalación:

1. No usa Alembic ni Mako; el esquema se crea con `Base.metadata.create_all()`.
2. No incluye un `uv.lock` generado en un índice privado. Docker instala desde el índice público de PyPI mediante `requirements.txt`, y FastAPI selecciona una versión compatible de Starlette.

## Opción recomendada: Docker Compose

Desde una copia limpia del proyecto:

```bash
cd /home/marvin/repos/GEO_AI/ponte_cachas_portal_postgresql
cp .env.example .env

docker compose down -v --remove-orphans
docker compose build --no-cache
docker compose up
```

Abre:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

Durante la construcción, Docker ejecuta una comprobación explícita de FastAPI, Starlette, SQLAlchemy, Jinja2, Psycopg y Uvicorn.

## Desarrollo local con `uv`

El ZIP no trae `uv.lock` deliberadamente. El primer `uv sync` generará uno nuevo usando PyPI en tu propio equipo:

```bash
cd /home/marvin/repos/GEO_AI/ponte_cachas_portal_postgresql
rm -rf .venv uv.lock
cp .env.example .env

docker compose up -d db
uv sync --no-dev
uv run python -m scripts.check_dependencies
uv run python -m scripts.init_db
uv run python -m scripts.seed_db
uv run uvicorn app:app --reload
```

Si tu instalación de `uv` tiene configurado otro índice global, fuerza PyPI:

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --no-dev --refresh
```

## Diagnóstico de Starlette

```bash
uv run python -c "import fastapi, starlette; print('FastAPI', fastapi.__version__, 'Starlette', starlette.__version__)"
```

También puedes ejecutar:

```bash
uv run python -m scripts.check_dependencies
```

Si sigue apareciendo un error de importación, elimina el entorno incompleto y vuelve a instalar:

```bash
rm -rf .venv uv.lock
uv cache clean starlette fastapi
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --no-dev --refresh
```

## Servicios y datos

- PostgreSQL como base de datos principal.
- Modelos SQLAlchemy para `users`, `centers`, `gym_classes` y `reservations`.
- Persistencia de inscripciones a clases y citas con entrenadores o dietistas.
- Prevención de reservas duplicadas y control transaccional de plazas.
- Semillas idempotentes para centros y clases.

## Endpoints principales

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/centers` | Lista centros persistidos |
| GET | `/api/classes` | Lista y filtra clases |
| POST | `/api/classes/enroll` | Inscribe a una clase y descuenta una plaza |
| POST | `/api/appointments` | Reserva entrenador o dietista |
| GET | `/api/reservations?email=...` | Consulta reservas |
| GET | `/health` | Comprueba la conexión a PostgreSQL |

## Nota sobre cambios del esquema

`create_all()` crea tablas que no existan, pero no migra columnas ya creadas. Durante la fase de demo puedes recrear el volumen tras modificar los modelos:

```bash
docker compose down -v
docker compose up --build
```
