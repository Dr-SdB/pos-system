#!/bin/bash
set -e
python manage.py migrate --noinput
python manage.py create_superuser_env
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --log-level debug
