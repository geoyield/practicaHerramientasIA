FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app

# Docker usa pip y requirements.txt para evitar lockfiles generados contra
# índices privados de otros entornos. El desarrollo local puede seguir usando uv.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m scripts.check_dependencies

EXPOSE 8000
# en render fallaba el deployment por 'connection to server at "127.0.0.1", port 5432 failed: Connection refused'. A sugenrencia de codex, de implementa esto. Previamente se había probado a comunicar via una network tipo bridge los dos containers, pero no soluiciona el problema
CMD ["sh", "-c", "python -m scripts.init_db && python -m scripts.seed_db && exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

