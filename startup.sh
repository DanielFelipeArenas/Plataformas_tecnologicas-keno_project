#!/bin/bash

echo "Starting Keno application..."

# Migrar base de datos
echo "Running migrations..."
python manage.py migrate --noinput

# Recolectar archivos estáticos
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Obtener puerto de Azure (o usar 8000 por defecto)
PORT="${PORT:-8000}"

echo "Starting Daphne server on port $PORT..."

# Iniciar servidor con Daphne
daphne -b 0.0.0.0 -p $PORT config.asgi:application