FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/backend/pyproject.toml
COPY alembic.ini /app/backend/alembic.ini
COPY alembic /app/backend/alembic
COPY catalogs /app/backend/catalogs
COPY src /app/backend/src

RUN pip install --no-cache-dir -e /app/backend

EXPOSE 8000

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh"]