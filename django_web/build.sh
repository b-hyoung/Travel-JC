#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [ "${RUN_SUPERUSER_SETUP}" = "1" ]; then
  python manage.py ensure_superuser
fi
