env/Scripts/activate
echo "Virtual env activated!"

cd amazon || exit

echo "Starting migrations..."
python3 manage.py migrate
echo "Finished migrations"

echo "Collecting static files..."
python3 manage.py collectstatic --no-input

echo "Starting scrapyd..."
rm /web_app/amazon/twistd.pid || true
scrapyd &

echo "Starting gunicorn"
python3 -m gunicorn webscraper.wsgi --bind 0.0.0.0:8000 --workers 2 --timeout 3600
