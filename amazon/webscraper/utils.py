from datetime import datetime
from datetime import timedelta
import json
import re
from django.utils import timezone
from uuid import uuid4

import gspread

from amazon.google_api import GoogleSheetsApi
from clusters.bulk import google_sheets_bulk
from clusters.cluster import google_sheets_clusters
from clusters.sponsored import create_sponsored, create_display
from clusters.table_utils import get_table_name
from clusters.term_report import create_term_report
from django.conf import settings
from uploaders.sponsor_products import run_amazon_media_uploader

from .celery import app
from .constants import COUNTRY_URLS, SEARCH_PATH, COUNTRY_COOKIES
from .models import AsinsMonitoring, AdvertisingMonitoring, Campaign
from .settings import APIKEY_FILEPATH, MEDIA_ROOT

DEFAULT_CAMPAIGN_TYPES = ['Seed', 'Exact TOP', 'Exact', 'Exact Low', 'Exact Other', 'Brands', 'Variation',
                          'Broad', 'Words', 'Category', 'Brand Defense', 'Self Targeting', 'Auto Close', 
                          'Auto Loose', 'Auto Subs', 'Auto Compl', 'negativephrases', 'negativepats']
# 'Auto Negatives Close', 'Auto Negatives Lose', 'Auto Negatives Subs', 'Auto Negatives Compl' - remove it because 


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
    company_types = ['seed', 'str_low', 'exact_other', 'variation', 'exact_top', 'exact', 'exact_low',
                     'broad', 'brands', 'tpa', 'tca', 'lsa', 'lpa', 'ca', 'ra', 'auto',
                     'auto_negatives', 'category', 'words', 'brand_def', 'adv_asin']

    pats = ['tpa', 'tca', 'lsa', 'lpa', 'ca', 'ra']

    company_values = {company: {'scu': '', 'bid': ''}
                      for company in company_types}
    for company in company_types:
        scu_key = f'{company}_scu'
        bid_key = f'{company}_bid'
        if company in pats:
            scu = data.get('pat_scu', "")
        else:
            scu = data.get(scu_key, "")
        bid = data.get(bid_key, "")
        company_values[company] = {'scu': scu, 'bid': bid}
    company_values['mkpc_key'] = data['mkpc_key']
    return company_values


def _get_url(keyword: str, country: str) -> str:
    return f'{COUNTRY_URLS[country]}{SEARCH_PATH}{keyword.replace(" ", "+")}'


def format_parse_args(keywords: str, negative_words: str, country: str) -> tuple:

    negative_words = ' '.join(
        [keyword for keyword in negative_words.split('\r\n')])
    links_to_serp = ' '.join([_get_url(keyword, country)
                             for keyword in keywords.split('\r\n')])
    return links_to_serp, negative_words


def _create_tables(table: str, cluster_status: bool, bulk_status: bool, sponsored_status: bool,
                   sponsored_video_status: bool, sponsored_display_status: bool, data: dict, bulk_upload_status: bool, request) -> list:
    filenames = []
    if cluster_status and bulk_status:
        clusters_values = get_company_values(data)
        google_sheets_clusters(table, clusters_values,
                               bulk_upload_status, request) 
        campaign_name, prefix  = get_campaigns(request)
        campaign_names = list(campaign_name.keys())
        cmp_ending = data.get("cmp_ending", "SP")
        bulk_file = google_sheets_bulk(
            table, campaign_names, cmp_ending, [""])
        filenames.append(bulk_file)
        
    elif cluster_status:
        clusters_values = get_company_values(data)
        google_sheets_clusters(table, clusters_values,
                               bulk_upload_status, request)  # еге
    elif bulk_status:
        print(f"data in _create_tables: {data}")
        campaign_data = [key.replace('campaign_', '') for key, value in data.items(
        ) if key.startswith('campaign_') and value == 'on']
        campaign_2_data = [key.replace('inner_camp_', '') for key, value in data.items(
        ) if key.startswith('inner_camp_') and value == 'on']
        cmp_ending = data.get("cmp_ending", "SP")
        # print(f"campaign_name when upload hear from site: {campaign_data}")
        bulk_file = google_sheets_bulk(
            table, campaign_data, cmp_ending, campaign_2_data)
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
        _write_statistic(table, request)
    return filenames


def _get_current_datetime() -> str:
    current_datatime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    return current_datatime


def _get_html_tag(table_link: str, request) -> str:
    table_name = get_table_name(table_link)
    link = f'<a href="{table_link}">{table_name}</a>'
    date = _get_current_datetime()
    username = request.user.username
    return f'<tr><td>{link}</td><td>{date}</td><td>{username}</td></tr>'


def _write_statistic(table, request):
    statistic_file = 'media/statistic.html'
    with open(statistic_file, 'r') as statistic:
        current_statistic = statistic.readlines()

    if '</table>' in ''.join(current_statistic):
        html_body = _get_html_tag(table, request)

        for index, line in enumerate(current_statistic):
            if '</table>' in line:
                current_statistic.insert(index, html_body)
                break

        with open(statistic_file, 'w') as statistic:
            statistic.writelines(current_statistic)
    else:
        html_body = _get_html_tag(table, request)
        with open(statistic_file, 'a+') as statistic:
            statistic.write(f'<table>\n{html_body}\n</table>')


def create_tables_manager(data: dict, request) -> list:
    clusters_google_sheet_link = data['clusters_google_sheet_link']
    asins_google_sheet_link = data['asins_google_sheet_link']
    asins_create_bulk = data.get('asins_create_bulk')
    sponsored_status = data.get('create_sponsored')
    sponsored_video_status = data.get('create_sponsored_video')
    sponsored_display_status = data.get('create_sponsored_display')
    clusters_status = data.get('clusters_create_clusters')
    bulk_status = data.get('clusters_create_bulk')
    bulk_upload_status = data.get("bulk_upload_link")

    if bulk_upload_status and asins_google_sheet_link:
        filename_clusters = _create_tables(clusters_google_sheet_link, clusters_status, bulk_status,
                                           sponsored_status, sponsored_video_status, sponsored_display_status,
                                           data, bulk_upload_status, request)
    filenames_asins = None
    if asins_create_bulk and asins_google_sheet_link:
        filenames_asins = _create_tables(
            asins_google_sheet_link, True, True, True, True, True, data, bulk_upload_status)
    filename_clusters = _create_tables(clusters_google_sheet_link, clusters_status, bulk_status,
                                       sponsored_status, sponsored_video_status, sponsored_display_status,
                                       data, bulk_upload_status, request)
    return filenames_asins or filename_clusters


def asins_scraper_manager(data: dict, scrapyd):
    # print(f"data dict: {data}")
    asins_google_sheet_link = data['asins_google_sheet_link']
    search_links = data['search_links']
    keywords = data['keywords']
    country = data['country']

    dv_asins = data['our_adv_asins']
    quality_search = data['quality_search']

    type_selection = data.getlist('type_selection')
    from_range = data.getlist('from_range')
    to_range = data.getlist('to_range')

    our_product_asins = data.getlist('asin_product')
    our_product_skus = data.getlist('sku_product')

    # print(
    #     f"our_product_asins: {our_product_asins}, our_product_skus: {our_product_skus}")

    read_creterians = create_range_dict(
        type_selection, from_range, to_range)

    if search_links and asins_google_sheet_link and country and quality_search:
        unique_id = str(uuid4())
        scrapyd_settings = {
            'unique_id': unique_id,
        }
        links_to_serp, negative_words = format_parse_args(
            search_links, keywords, country)
        cookie = COUNTRY_COOKIES[country]
        sp_asins = ' '.join(our_product_asins)
        sp_skus = ' '.join(our_product_skus)
        adv_asins = ' '.join(dv_asins.split('\r\n'))
        task = scrapyd.schedule('default', 'amazon', settings=scrapyd_settings,
                                keywords=negative_words, sp_def_skus=sp_skus,
                                table_link=asins_google_sheet_link, limit=quality_search,
                                urls=links_to_serp, sp_def_asins=sp_asins,
                                adv_variations_asins=adv_asins, creterians=json.dumps(
                                    read_creterians),
                                apikey_file_path=settings.APIKEY_FILEPATH, cookie=cookie)


def create_range_dict(type_selection, from_range, to_range):
    result = {}

    for i, key in enumerate(type_selection):
        from_value = from_range[i] if i < len(
            from_range) and from_range[i] != '' else None
        to_value = to_range[i] if i < len(
            to_range) and to_range[i] != '' else None
        difficult_key = f"{key}_{from_range[i]}-{to_range[i]}"
        result[difficult_key] = [from_value, to_value]
    # tut ya zroblu щоб повертався список з усыма критериями
    # result = {'price_1-3': [1, 3],  'price_3-10': [3, 10], 'price_10-': [10, None],}
    print(f"result: {result}")
    return result


def search_term_report_manager(data: dict, files: dict) -> str:
    file1, file2 = files['file1'].read(), files['file2'].read()
    all_products = data.get('all_products_status')
    products1 = data.get('report_campaign_1')
    products2 = data.get('report_campaign_2')
    products = None
    if products1 and products2:
        products1 = products1.split('\r\n')
        products2 = products2.split('\r\n')
        products = {products1[elem]: products2[elem]
                    for elem in range(len(products1))}
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
    scrapyd.schedule('default', 'asins_monitoring',
                     settings=scrapyd_settings, **monitoring_params)


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
    scrapyd.schedule('default', 'advertising_monitoring',
                     settings=scrapyd_settings, **monitoring_params)


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


def to_snake_case(name):
    new_name = name.lower()
    new_name = re.sub(r'\s+', '_', new_name)
    new_name = new_name.strip('_')
    # print(f"name before: {name} <-> name after: {new_name}")
    return new_name


def extract_text(input_string):
    match = re.search(r'\(([^)]+)\)', input_string)
    if match:
        return match.group(1) + input_string.split(')')[1]
    return None


def get_campaigns(request) -> list:
    user_id = request.user.id
    current_time = timezone.now()
    campaigns = Campaign.objects.filter(user_id=user_id)
    if campaigns.exists():
        # print(f"campaigns in get_campaigns from db: {campaigns}")
        # first_campaign = campaigns.first()
        # time_difference = current_time - first_campaign.created_at
        # if time_difference < timedelta(days=3):
        #     result = {to_snake_case(campaign.name)
        #                             : campaign.name for campaign in campaigns}
        # else:
        result = {to_snake_case(
                default_campaign): default_campaign for default_campaign in DEFAULT_CAMPAIGN_TYPES}
        prefix = "inner_camp"
    else:
        result = {to_snake_case(
            default_campaign): default_campaign for default_campaign in DEFAULT_CAMPAIGN_TYPES}

    print(f"result: {result}")
    return result, prefix


def get_table_id(table_link) -> str:
    return table_link.split('/d/')[1].split('/')[0]


def extract_text_from_name(input_string):
    # Перший випадок: "Team Cards | SEED" - повертаємо "SEED"
    match = re.search(r'\|\s*([A-Z]+)$', input_string)
    if match:
        return match.group(1)

    # Другий випадок: "Team Cards | PAT - RA" - повертаємо "PAT | RA"
    match = re.search(r'\|\s*([A-Z]+)\s*-\s*([A-Z]+)', input_string)
    if match:
        return f"{match.group(1)} | {match.group(2)}"
    
    # Новий випадок з трьома крапками: "Z Blast | PAT - lpa 10...100 2" -> "PAT - lpa 10...100"
    match = re.search(r"\|\s*([A-Z]+ - .*\.{3}.*?)(?:\s+\d+)?$", input_string)
    if match:
        return match.group(1).strip()

    # Третій випадок: Витягнути все після "|"
    match = re.search(r'\|\s*(.+?)\s*\d*$', input_string)
    if match:
        return match.group(1).strip()

    return None


def to_snake_case_for_name(name):
    new_name = name.lower()
    new_name = re.sub(r'\s+', '_', new_name)
    # new_name = new_name.replace('-', '|')
    new_name = new_name.strip('_')
    # print(f"name before: {name} <-> name after: {new_name}")
    return new_name

def upload_info_from_table(table_link, request):
    table_id = get_table_id(table_link)

    gc = gspread.service_account(filename='amazon/apikey.json')
    sht1 = gc.open_by_key(table_id)

    worksheet_objs = sht1.worksheets()
    for worksheet in worksheet_objs:
        if 'clusters' in worksheet.title.lower():
            tab_name = worksheet.title

    worksheet = sht1.worksheet(tab_name)
    camaign_names = worksheet.row_values(2)

    filtered_campaign_name = dict()
    for camaign_name in camaign_names:
        print(f"camaign_name from table: {camaign_name}")
        if camaign_name != "" and camaign_name != " ":
            filter_campaign_name = extract_text_from_name(camaign_name)
            print(f"filter_campaign_name: {filter_campaign_name}")
            filter_campaign_name_snake_case = to_snake_case_for_name(filter_campaign_name)
            print(f"filter_campaign_name_snake_case: {filter_campaign_name_snake_case}")

            if filter_campaign_name_snake_case not in filtered_campaign_name.keys():
                filtered_campaign_name[filter_campaign_name_snake_case] = camaign_name
    upload_campaign_to_db(request, filtered_campaign_name.values())
    for key, value  in filtered_campaign_name.items():
        filtered_campaign_name[key] = value.split(" | ")[1]
    return filtered_campaign_name


def upload_campaign_to_db(request, campaign_names):
    user_id = request.user.id

    campaigns = list()
    filter_campaign_names = list()
    # print(f"campaign_names: {campaign_names}")
    unique_campaign_names = list(dict.fromkeys(campaign_names))

    for campaign_name in unique_campaign_names:
        filter_campaign_names.append(extract_text_from_name(campaign_name))
    

    unique_campaign_names = list(dict.fromkeys(filter_campaign_names))
    Campaign.objects.filter(user_id=user_id).delete()
    for campaign_name in unique_campaign_names:
        # print(f"campaign_name_to_save: {campaign_name}")

        campaigns.append(Campaign(name=campaign_name, user_id=user_id))
        
    Campaign.objects.bulk_create(campaigns)
    
def filter_negative_topics(campaign_names):
    negative_pats = []
    negative_exact_and_phrase = []

    auto_negatives = ["auto_negatives_close", "auto_negatives_loose", "auto_negatives_subs", "auto_negatives_compl"]

    campaign_names_copy = campaign_names.copy()
    for item, value in campaign_names_copy.items():
        if item.startswith("pat"):
            campaign_names["negativepats"] = "Negative PATs"
            negative_pats.append(item)
            campaign_names.pop(item, None)
        elif item in auto_negatives:
            campaign_names["negativephrases"] = "Negative Phrases"
            negative_exact_and_phrase.append(item)
            campaign_names.pop(item, None) 
    
    return campaign_names, negative_pats, negative_exact_and_phrase