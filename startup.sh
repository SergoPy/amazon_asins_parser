#!/bin/bash

# Активуємо віртуальне середовище
source /web_app_v2/env/bin/activate
echo "Virtual env activated!"

# Переходимо в каталог проекту
cd amazon || exit

# Виконуємо міграції
echo "Starting migrations..."
python3 manage.py migrate
echo "Finished migrations"

# Збираємо статичні файли
echo "Collecting static files..."
python3 manage.py collectstatic --no-input

# Запускаємо Scrapyd
echo "Starting scrapyd..."
find /web_app_v2/amazon -name "twistd.pid" -delete || true
scrapyd &

# Запускаємо Gunicorn
echo "Starting gunicorn"
gunicorn webscraper.wsgi:application --bind 0.0.0.0:8009 --workers 2 --timeout 3600
