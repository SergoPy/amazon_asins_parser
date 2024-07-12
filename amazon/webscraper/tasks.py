from datetime import datetime, timedelta
from uuid import uuid4

from webscraper import settings
from django.forms.models import model_to_dict
from webscraper.models import AsinsMonitoring, AdvertisingMonitoring

from webscraper.celery import app


#@app.task
def start_spider(spider_name: str, monitoring_params: dict):
    monitoring_params['apikey_filepath'] = settings.APIKEY_FILEPATH
    unique_id = str(uuid4())
    scrapyd_settings = {
        'unique_id': unique_id,
    }
    settings.scrapyd.schedule('default', spider_name, settings=scrapyd_settings, **monitoring_params)


@app.task
def start_asins_monitoring():
    tasks = AsinsMonitoring.objects.all()
   
    task: AsinsMonitoring
    for task in tasks:
        now = datetime.now(task.last_run.tzinfo)
        if now >= task.last_run + timedelta(days=task.frequency):
            task.last_run = now
            task.save()
            start_spider('asins_monitoring', model_to_dict(task))



@app.task
def start_advertising_monitoring():
    tasks = AdvertisingMonitoring.objects.all()
    task: AdvertisingMonitoring
    for task in tasks:
        now = datetime.now(task.last_run.tzinfo)
        if now >= task.last_run + timedelta(days=task.frequency):
            start_spider.delay('adv_monitoring', model_to_dict(task))
            task.last_run = now
            task.save()
