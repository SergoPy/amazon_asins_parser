from celery import Celery
from celery.schedules import crontab

from . import settings

app = Celery('webscraper', broker=settings.CELERY_BROKER_URL)

app.conf.beat_schedule = {
    'start-asins-monitoring': {
        'task': 'webscraper.tasks.start_asins_monitoring',
        'schedule': crontab(day_of_month='*/2')
    },
    'start-advertising-monitoring': {
        'task': 'webscraper.tasks.start_advertising_monitoring',
        'schedule': crontab(day_of_month='*/2')
    },
}
