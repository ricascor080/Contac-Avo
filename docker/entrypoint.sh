#!/bin/sh
# Aplica migraciones pendientes antes de arrancar la app.
set -e
python manage.py migrate --noinput
exec "$@"
