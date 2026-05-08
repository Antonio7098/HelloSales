#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
alembic upgrade head

echo "Starting application..."
exec uvicorn hello_sales_backend.app:app --host 0.0.0.0 --port $PORT