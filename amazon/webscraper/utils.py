from datetime import datetime
from uuid import uuid4

from clusters.bulk import google_sheets_bulk
from clusters.cluster import google_sheets_clusters
from clusters.sponsored import create_sponsored, create_display
from clusters.table_utils import get_table_name
from clusters.term_report import create_term_report
from django.conf import settings
from uploaders.sponsor_products import run_amazon_media_uploader

from .celery import app
from .constants import COUNTRY_URLS, SEARCH_PATH, COUNTRY_COOKIES
from .models import AsinsMonitoring, AdvertisingMonitoring
from .settings import MEDIA_ROOT


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_company_sponsored_values(data: dict) -> dict:
    company_types = ['tpa', 'tca', 'lsa', 'lpa', 'ca', 'ra', 'category']
    values = {company: data[f'sb_{company}_bid'] for company in company_types}
    values['optimization_type'] = data['optimization_type']
    return values


def get_company_values(data: dict) -> dict:
    company_types = ['tpk', 'str_low', 'str_top', 'variation', 'exact_top', 'exact', 'exact_low',
                     'broad', 'brands', 'tpa', 'tca', 'lsa', 'lpa', 'ca', 'ra', 'auto',
                     'auto_negatives', 'category']

    pats = ['tpa', 'tca', 'lsa', 'lpa', 'ca', 'ra']

    company_values = {company: {'scu': '', 'bid': ''} for company in company_types}
    for company in company_types:
        scu_key = f'{company}_scu'
        bid_key = f'{company}_bid'
        if company in pats:
            scu = data['pat_scu']
        else:
            scu = data[scu_key]
        bid = data[bid_key]
        company_values[company] = {'scu': scu, 'bid': bid}

    return company_values


def _get_url(keyword: str, country: str) -> str:
    return f'{COUNTRY_URLS[country]}{SEARCH_PATH}{keyword.replace(" ", "+")}'


def format_parse_args(keywords: str, negative_words: str, country: str) -> tuple:
    negative_words = ' '.join([keyword for keyword in negative_words.split('\r\n')])
    links_to_serp = ' '.join([_get_url(keyword, country) for keyword in keywords.split('\r\n')])
    return links_to_serp, negative_words


def _create_tables(table: str, cluster_status: bool, bulk_status: bool, sponsored_status: bool,
                   sponsored_video_status: bool, sponsored_display_status: bool, data: dict) -> list:
    filenames = []
    if cluster_status:
        clusters_values = get_company_values(data)
        google_sheets_clusters(table, clusters_values)
    if bulk_status:
        bulk_file = google_sheets_bulk(table)
        filenames.append(bulk_file)
    if sponsored_status:
        sponsored_file = create_sponsored(table, data)
        filenames.append(sponsored_file)
    if sponsored_video_status:
        sponsored_video_file = create_sponsored(table, data, video=True)
        filenames.append(sponsored_video_file)
    if sponsored_display_status:
        values = get_company_sponsored_values(data)
        sponsored_display_file = create_display(table, values)
        filenames.append(sponsored_display_file)
    if any([bulk_status, cluster_status, sponsored_status, sponsored_video_status, sponsored_display_status]):
        _write_statistic(table)
    return filenames


def _get_current_datetime() -> str:
    current_datatime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    return current_datatime


def _get_html_tag(table_link: str) -> str:
    table_name = get_table_name(table_link)
    link = f'<a href="{table_link}">{table_name}</a>'
    date = _get_current_datetime()
    return f'<tr><td>{link}</td><td>{date}</td></tr>'


def _write_statistic(table):
    statistic_file = 'media/statistic.html'
    with open(statistic_file, 'r') as statistic:
        current_statistic = statistic.readlines()
    with open(statistic_file, 'a+') as statistic:
        if table not in ''.join(current_statistic):
            html_body = _get_html_tag(table)
            statistic.write(html_body)


def create_tables_manager(data: dict) -> list:
    clusters_google_sheet_link = data['clusters_google_sheet_link']
    asins_google_sheet_link = data['asins_google_sheet_link']
    asins_create_bulk = data.get('asins_create_bulk')
    sponsored_status = data.get('create_sponsored')
    sponsored_video_status = data.get('create_sponsored_video')
    sponsored_display_status = data.get('create_sponsored_display')
    clusters_status = data.get('clusters_create_clusters')
    bulk_status = data.get('clusters_create_bulk')

    filenames_asins = None
    if asins_create_bulk and asins_google_sheet_link:
        filenames_asins = _create_tables(asins_google_sheet_link, True, True, True, True, True, data)
    filename_clusters = _create_tables(clusters_google_sheet_link, clusters_status, bulk_status,
                                       sponsored_status, sponsored_video_status, sponsored_display_status,
                                       data)
    return filenames_asins or filename_clusters


def asins_scraper_manager(data: dict, scrapyd):
    asins_google_sheet_link = data['asins_google_sheet_link']
    search_links = data['search_links']
    keywords = data['keywords']
    country = data['country']
    asins = data['asins']
    quality_search = data['quality_search']
    price_filter = data['price_filter']
    review_filter = data['review_filter']
    rating_filter = data['rating_filter']

    if search_links and asins_google_sheet_link and country and quality_search:
        unique_id = str(uuid4())
        scrapyd_settings = {
            'unique_id': unique_id,
        }
        links_to_serp, negative_words = format_parse_args(search_links, keywords, country)
        cookie = COUNTRY_COOKIES[country]
        sp_asins = ' '.join(asins.split('\r\n'))
        task = scrapyd.schedule('default', 'amazon', settings=scrapyd_settings, price_filter=price_filter,
                                review_filter=review_filter, rating_filter=rating_filter,
                                keywords=negative_words, table_link=asins_google_sheet_link,
                                limit=quality_search, urls=links_to_serp, sp_def_asins=sp_asins,
                                apikey_file_path=settings.APIKEY_FILEPATH, cookie=cookie)

def search_term_report_manager(data: dict, files: dict) -> str:
    file1, file2 = files['file1'].read(), files['file2'].read()
    all_products = data.get('all_products_status')
    products1 = data.get('report_campaign_1')
    products2 = data.get('report_campaign_2')
    products = None
    if products1 and products2:
        products1 = products1.split('\r\n')
        products2 = products2.split('\r\n')
        products = {products1[elem]: products2[elem] for elem in range(len(products1))}
    if file1 and file2:
        create_term_report(file1, file2, products, all_products)
        return settings.TERM_REPORT_FILENAME


@app.task
def run_asins_monitoring(data: dict, scrapyd) -> None:
    country = data['monitoring_country']

    monitoring_params = {
        'seller_name': data['seller_name'],
        'product_name': data['product_name'],
        'personal_asin': data['personal_asin'],
        'competitor_asins': data['competitor_asins'],
        'keywords': data['keywords'],
        'google_sheet_link': data['asins_google_sheet_link'],
        'frequency': data['frequency'],
        'country_cookie': COUNTRY_COOKIES[country],
        'base_url': COUNTRY_URLS[country]
    }

    save_monitoring(AsinsMonitoring, monitoring_params)

    monitoring_params['apikey_filepath'] = settings.APIKEY_FILEPATH
    unique_id = str(uuid4())
    scrapyd_settings = {
        'unique_id': unique_id,
    }
    scrapyd.schedule('default', 'asins_monitoring', settings=scrapyd_settings, **monitoring_params)

@app.task
def run_advertising_monitoring(data: dict, scrapyd) -> None:
    country = data['monitoring_country_adv']

    monitoring_params = {
        'asins': data['asins_adv'],
        'google_sheet_link': data['asins_google_sheet_link_adv'],
        'category': data['category_adv'],
        'login': data['login_adv'],
        'password': data['password_adv'],
        'account_name': data['account_name_adv'],
        'product_name': data['product_name_adv'],
        'start_date': data['start_date_adv'],
        'end_date': data['end_date_adv'],
        'target_acos': data['target_acos_adv'],
        'entity_id': data['entity_id_adv'],
        'base_url': COUNTRY_URLS[country]
    }

#    save_monitoring(AsinsMonitoring, monitoring_params)

    monitoring_params['apikey_filepath'] = settings.APIKEY_FILEPATH
    unique_id = str(uuid4())
    scrapyd_settings = {
        'unique_id': unique_id,
    }
    scrapyd.schedule('default', 'advertising_monitoring', settings=scrapyd_settings, **monitoring_params)


def save_monitoring(monitoring_model, data: dict) -> None:
    data['last_run'] = datetime.now()
    asins_monitoring = monitoring_model(**data)
    asins_monitoring.save()


def handle_uploaded_file(file):
    if file:
        filepath = f'{MEDIA_ROOT}{file.name}'
        with open(filepath, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return filepath


def run_campaign_upload(data: dict, files: dict):
    upload_kwargs = {
        'login': data['login'],
        'password': data['password'],
        'creative_asins': data['creative_asins'],
        'headline': data.get('headline'),
        'base_domain': COUNTRY_URLS[data['sb_country']],
        'logo': handle_uploaded_file(files.get('sb_logo')),
        'media': handle_uploaded_file(files.get('sb_media')),
        'media_sbv': handle_uploaded_file(files.get('sbv_media')),
        'table_link': data['clusters_google_sheet_link'],
        'apikey_filepath': settings.APIKEY_FILEPATH,
        'bid_mode': data.get('bids') if data.get('bids') else '0',
        'brand_name': data['brand_name'],
        'entity_id': data['brand_entity_id']
    }
    upload_mode = data['upload_campaign_mode']
    run_amazon_media_uploader(upload_kwargs, upload_mode)
