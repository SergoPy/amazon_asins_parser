from django.db.models import Model, CharField, TextField, IntegerField, URLField, DateTimeField


class Monitoring(Model):
    created_at = DateTimeField(auto_now_add=True)
    seller_name = CharField(max_length=64)
    product_name = CharField(max_length=64)
    frequency = IntegerField()
    google_sheet_link = URLField()
    last_run = DateTimeField()

    def __str__(self):
        return f"{self.seller_name} - {self.product_name}"

    class Meta:
        abstract = True


class AsinsMonitoring(Monitoring):
    personal_asin = CharField(max_length=10)
    competitor_asins = CharField(max_length=100)
    keywords = TextField()
    base_url = URLField()
    country_cookie = TextField()


class AdvertisingMonitoring(Monitoring):
    asins = CharField(max_length=255)
    target_acos = IntegerField()
    entity_id = CharField(max_length=32)
    login = CharField(max_length=64)
    password = CharField(max_length=64)
