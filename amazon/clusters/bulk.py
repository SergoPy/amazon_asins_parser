import csv
import re
import gspread
import pandas as pd
import numpy as np
import httplib2
import sys
from googleapiclient.errors import HttpError


from googleapiclient import discovery
from datetime import date, datetime

# from amazon.amazon.spiders import asins_monitoring
from webscraper.settings import MEDIA_ROOT

API_KEY = 'AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY'
COLUMNS = ['Product', 'Entity', 'Operation', 'Campaign Id', 'Ad Group Id', 'Portfolio Id', 'Ad Id (Read only)',
           'Keyword Id (Read only)', 'Product Targeting Id (Read only)', 'Campaign Name', 'Ad Group Name',
           'Campaign Name (Informational only)', 'Ad Group Name (Informational only)',
           'Portfolio Name (Informational only)', 'Start Date', 'End Date', 'Targeting Type', 'State',
           'Campaign State (Informational only)', 'Ad Group State (Informational only)', 'Daily Budget', 'SKU',
           'ASIN (Informational only)', 'Eligibility Status (Informational only)',
           'Reason for ineligibility (Informational only)', 'Ad Group Default Bid',
           'Ad Group Default Bid (Informational only)', 'Bid', 'Keyword Text', 'Match Type', 'Bidding Strategy',
           'Placement', 'Percentage', 'Product Targeting Expression',
           'Resolved Product Targeting Expression (Informational only)', 'Impressions', 'Clicks', 'Click-through Rate',
           'Spend', 'Sales', 'Orders', 'Units', 'Conversion Rate', 'Acos', 'CPC', 'ROAS']
cmp_ending = ''


def get_data_frame(key, spreadsheet_id, range_name):
    discovery_url = ('https://sheets.googleapis.com/$discovery/rest?'
                     'version=v4')
    service = discovery.build(
        'sheets',
        'v4',
        http=httplib2.Http(),
        discoveryServiceUrl=discovery_url,
        developerKey=key
    )

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    # print(f"get_data_frame: {result}")
    values = result.get('values', [])
    # print(f"get_data_frame_value: {values}")

    return pd.DataFrame(values)


def make_brand_def_all(brand_deff_total_data, data):
    asins = []
    skus = []
    for item in brand_deff_total_data:
        if item is not None and "|" in item:
            asin, sku = item.split("|", 1)
            asins.append(asin)
            skus.append(sku)

    all_brand_deff_dfs = []
    for index, sku in enumerate(skus):
        data[0] = asins[index]
        target_asins_list = asins.copy()
        target_asins_list.pop(index)
        cur_df = make_brand_def_one(target_asins_list, [sku], data)
        all_brand_deff_dfs.append(cur_df)

    return pd.concat(all_brand_deff_dfs).reset_index().drop('index', axis=1)


def create_company_name(data, keyword=''):
    global_company_name = data[0].split("|")[0]
    company_type_tmp = data[0].split("|")[1]
    if '-' in company_type_tmp:
        company_type = company_type_tmp.split("-")[0]
        if keyword == '':
            keyword = "- " + company_type_tmp.split("-")[1]
    else:
        company_type = company_type_tmp

    if keyword and not keyword.startswith('-'):
        keyword = "- " + keyword

    new_name = f"{global_company_name}|{company_type} {keyword} | "
    new_name = re.sub(r'\s{2,}', ' ', new_name)
    return [new_name]


def make_brand_def_one(asins, sku, data):
    skus = [x.strip() for x in sku[0].split(',') if x]
    global cmp_ending
    total_def_len = 4 + len(asins) + len(skus)
    str_asins = ['asin="' + x +
                 '"' for x in asins if x is not None and x != '']
    none = [None] * total_def_len
    # data: ["Advertised ASIN", "galon clear jojoba oil ", "Brand Defense", "bid(seed)"]
    # broad items = sku
    # broad_words = asins
    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_def_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] +
        ['Product Ad'] * len(skus) + ['Product targeting'] * len(asins),
        ['Create'] * total_def_len,
        [data[1].split("|")[0] +
         f'| {data[2]} | {data[0]} {cmp_ending}'] * total_def_len,
        [None] * 3 + [data[2]] * (1 + len(asins) + len(skus)),
        none, none, none, none,
        [data[1].split("|")[
            0] + f'| {data[2]} | {data[0]} {cmp_ending}'] + [None] * (total_def_len - 1),
        [None] * 3 + [data[2]] + [None] * (total_def_len - 4),
        none,
        [None] * 3 + [data[2]] * (1 + len(asins) + len(skus)),
        none,
        [str(date.today()).replace('-', '')] + [None] * (total_def_len - 1),
        none,
        ['MANUAL'] + [None] * (total_def_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_def_len - 3),
        ['enabled'] * total_def_len,
        [None] * 3 + ['enabled'] * (1 + len(asins) + len(skus)),
        [300] + [None] * (total_def_len - 1),
        [None] * 4 + skus + [None] * (total_def_len - 4 - len(skus)),
        none,
        [None] * 4 + ['Eligible'] * len(skus) + [None] * (total_def_len - 4 - len(skus)),
        none,
        [None] * 3 + [data[3]] + [None] * (total_def_len - 4),
        none,
        [None] * (4 + len(skus)) + [data[3]] * len(asins),
        none,
        none,
        ['Dynamic bids - down only'] * 3 + [None] * (total_def_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_def_len - 3),
        [None, 0, 0] + [None] * (total_def_len - 3),
        [None] * (4 + len(skus)) + list(str_asins),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_brand_advertised_asins(data):
    # print(f"data[0]: {data}")
    global cmp_ending
    adv_items = [x.strip() for x in data[4][0].split(',') if x]
    total_def_len = 4 + len(data[0]) + len(adv_items)
    str_asins = ['asin="' + x + '"' for x in data[0]
                 if x is not None and x != '']
    none = [None] * total_def_len
    # data: ["Advertised ASIN", "galon clear jojoba oil ", "Brand Defense", "bid(seed)", sku]
    # broad items = sku
    # broad_words = asins
    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_def_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] +
        ['Product Ad'] * len(adv_items) + ['Product targeting'] * len(data[0]),
        ['Create'] * total_def_len,
        [data[1].split(
            "|")[0] + f'| Self | {data[0][0]} {cmp_ending}'] * total_def_len,
        [None] * 3 + [data[2]] * (1 + len(data[0]) + len(adv_items)),
        none, none, none, none,
        [data[1].split(
            "|")[0] + f'| Self | {data[0][0]} {cmp_ending}'] +
        [None] * (total_def_len - 1),
        [None] * 3 + [data[2]] + [None] * (total_def_len - 4),
        none,
        [None] * 3 + [data[2]] * (1 + len(data[0]) + len(adv_items)),
        none,
        [str(date.today()).replace('-', '')] + [None] * (total_def_len - 1),
        none,
        ['MANUAL'] + [None] * (total_def_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_def_len - 3),
        ['enabled'] * total_def_len,
        [None] * 3 + ['enabled'] * (1 + len(data[0]) + len(adv_items)),
        [300] + [None] * (total_def_len - 1),
        [None] * 4 + adv_items + [None] * (total_def_len - 4 - len(adv_items)), 
        none,
        [None] * 4 + ['Eligible'] * len(adv_items) + [None] * (total_def_len - 4 - len(adv_items)),
        none,
        [None] * 3 + [data[3]] + [None] * (total_def_len - 4),
        none,
        [None] * (4 + len(adv_items)) + [data[3]] * len(data[0]),
        none,
        none,
        ['Dynamic bids - down only'] * 3 + [None] * (total_def_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_def_len - 3),
        [None, 0, 0] + [None] * (total_def_len - 3),
        [None] * (4 + len(adv_items)) + list(str_asins),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_seed_one(seed_data, word, target_asin, tos):
    global cmp_ending
    seed_items = [x.strip() for x in seed_data[2].split(',') if x]
    total_seed_len = 5 + len(seed_items)
    title = create_company_name(seed_data, keyword=word)

    none = [None] * total_seed_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_seed_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] +
        ['Product Ad'] * len(seed_items) + ['Keyword'],
        ['Create'] * total_seed_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_seed_len,  
        [None] * 3 + [seed_data[1]] *
        (total_seed_len - 3), none, none, none, none,
        [title[0] + target_asin + f' {cmp_ending}'] +
        [None] * (total_seed_len - 1),
        [None] * 3 + [seed_data[1]] + [None] * (total_seed_len - 4), none,
        [None] * 3 + [seed_data[1]] * (total_seed_len - 3), none,
        [str(date.today()).replace('-', '')] +
        [None] * (total_seed_len - 1), none,
        ['MANUAL'] + [None] * (total_seed_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_seed_len - 3),
        ['enabled'] * total_seed_len,
        [None] * 3 + ['enabled'] * (total_seed_len - 3),
        [300] + [None] * (total_seed_len - 1),
        [None] * 4 + seed_items + [None], 
        none,
        [None] * 4 + ['Eligible'] * len(seed_items) + [None], none,
        [None] * 3 + [seed_data[-1]] + [None] * (total_seed_len - 4), none,
        [None] * (total_seed_len - 1) + [seed_data[-1]],
        [None] * (total_seed_len - 1) + [word],
        [None] * (total_seed_len - 1) + ['exact'],
        ['Dynamic bids - down only'] * 3 + [None] * (total_seed_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_seed_len - 3),
        [None, 0, tos] + [None] * (total_seed_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_seed_all(seed_total_data, target_asin, tos):
    seed_data = seed_total_data[:4]
    seed_words = [x for x in seed_total_data[4:] if x]

    all_seed_dfs = []
    for k in seed_words:
        cur_df = make_seed_one(seed_data, k, target_asin, tos)
        all_seed_dfs.append(cur_df)

    return pd.concat(all_seed_dfs).reset_index().drop('index', axis=1)


def make_broad_all(broad_total_data, keyword_negatives, phrases_negatives, target_asin):
    global cmp_ending
    broad_data = broad_total_data[:4]
    broad_words = [f"'{x}" for x in broad_total_data[4:]
                   if x is not None and x != '']

    try:
        broad_items = [x.strip() for x in broad_data[2].split(',') if x]
    except AttributeError:
        broad_items = []
    total_broad_len = 4 + len(broad_items) + len(broad_words) + \
        len(keyword_negatives) + len(phrases_negatives)

    none = [None] * total_broad_len

    title = create_company_name(broad_total_data)

    # print(f"broad_data: {broad_data}, broad_words: {broad_words}, broad_items: {broad_items}, total_broad_len: {total_broad_len}\n broad_total_data:{broad_total_data}\n keyword_negatives: {keyword_negatives} \n phrases_negatives: {phrases_negatives}")
    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_broad_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(broad_items) + [
            'Keyword'] * len(broad_words) +
        ['Campaign Negative Keyword'] *
        (len(keyword_negatives) + len(phrases_negatives)),
        ['Create'] * total_broad_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_broad_len,
        [None] * 3 + [broad_data[1]] * (1 + len(broad_items) + len(broad_words)) + [None] * (len(keyword_negatives) + len(phrases_negatives)),#this
        none, none, none, none,
        [title[0] + target_asin + f' {cmp_ending}'] + [None] * (total_broad_len - 1),
        [None] * 3 + [broad_data[1]] + [None] * (total_broad_len - 4), 
        none,
        [None] * 3 + [broad_data[1]] * (1 + len(broad_items) + len(broad_words)) + [None] * (len(keyword_negatives) + len(phrases_negatives)), #this
        none,
        [str(date.today()).replace('-', '')] +
        [None] * (total_broad_len - 1), none,
        ['MANUAL'] + [None] * (total_broad_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_broad_len - 3),
        ['enabled'] * total_broad_len,
        [None] * 3 + ['enabled'] * (1 + len(broad_items) + len(broad_words)) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)),
        [300] + [None] * (total_broad_len - 1),
        [None] * 4 + broad_items + [None] *
        (total_broad_len - 4 - len(broad_items)), none,
        [None] * 4 + ['Eligible'] * len(broad_items) + [None] * (total_broad_len - 4 - len(broad_items)), 
        none,
        [None] * 3 + [broad_data[-1]] + [None] *  (total_broad_len - 4), 
        none,
        [None] * (4 + len(broad_items)) + [broad_data[-1]] * len(broad_words) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)),
        [None] * (4 + len(broad_items)) + list(broad_words) +                          
        list(keyword_negatives) + list(phrases_negatives),
        [None] * (4 + len(broad_items)) + ['Broad'] * len(broad_words) + ['negativeExact'] * len(
            keyword_negatives) +
        ['negativePhrase'] * len(phrases_negatives),
        ['Dynamic bids - down only'] * 3 + [None] * (total_broad_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_broad_len - 3),                                                                     
        [None, 0, 0] + [None] * (total_broad_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)

                                        
def make_auto_neg_all(auto_neg_total_data, keyword_negatives, phrases_negatives, target_asin, pte):
    global cmp_ending
    auto_neg_data = auto_neg_total_data[:4]
    auto_neg_items = [x.strip() for x in auto_neg_data[2].split(',')]

    total_auto_neg_len = 4 + \
        len(auto_neg_items) + len(keyword_negatives) + \
        len(phrases_negatives) + 4
    index_of_enabled = pte.index('enabled')
    bids = ['', '', '', '']
    bids[index_of_enabled] = auto_neg_data[-1]
    # print(f"len(keyword_negatives): {len(keyword_negatives)}")
    # print(f"keyword_negatives: {keyword_negatives}")
    # print(f"len(phrases_negatives): {len(phrases_negatives)}")
    # print(f"phrases_negatives: {phrases_negatives}")
    # print(f"auto_neg_total_data: {auto_neg_total_data}")

    title = create_company_name(auto_neg_total_data)

    none = [None] * total_auto_neg_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_auto_neg_len,  # 1 - 70
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(auto_neg_items) +
        ['Product Targeting'] * 4 + ['Campaign Negative Keyword'] * \
        (len(keyword_negatives) + len(phrases_negatives)),  # 2 - 70
        ['Create'] * total_auto_neg_len,  # 3 -70
        [title[0] + target_asin + f' {cmp_ending}'] * total_auto_neg_len,  # 4 -70
        [None] * 3 + [auto_neg_data[1]] * (total_auto_neg_len - 3),  # 5 - 70  #this
        none,  # 6
        none,  # 7
        none,  # 8
        none,  # 9
        [title[0] + target_asin + f' {cmp_ending}'] + [None] * (total_auto_neg_len - 1),  # 10 - 70
        [None] * 3 + [auto_neg_data[1]] + [None] * \
        (total_auto_neg_len - 4),  # 11 - 70
        none,  # 12
        [None] * 3 + [auto_neg_data[1]] * (1 + len(auto_neg_items) + 4) + [None] * (total_auto_neg_len - 8 - len(auto_neg_items)),  # 13 - 70 #this
        none,  # 14
        [str(date.today()).replace('-', '')] + [None] * \
        (total_auto_neg_len - 1),  # 15 - 70
        none,  # 16
        ['AUTO'] + [None] * (total_auto_neg_len - 1),  # 17 -70
        ['enabled'] + [None] * 2 + ['enabled'] * (len(auto_neg_items) + 1) + pte + ['enabled'] * (
            total_auto_neg_len - 8 - len(auto_neg_items)),  # 18 --------------------------------------------72 -------70
        ['enabled'] * total_auto_neg_len,  # 19 - 70
        [None] * 3 + ['enabled'] * (1 + len(auto_neg_items)) + [None] * (
            total_auto_neg_len - 4 - len(auto_neg_items)),  # 20 - 70
        [300] + [None] * (total_auto_neg_len - 1),  # 21 - 70
        [None] * 4 + auto_neg_items + [None] * \
        (total_auto_neg_len - len(auto_neg_items) - 4),  # 22 - 70
        none,  # 23
        [None] * 4 + ['Eligible'] * len(auto_neg_items) + [None] * (
            total_auto_neg_len - 4 - len(auto_neg_items)),  # 24 - 70
        none,  # 25
        [None] * 3 + [auto_neg_data[-1]] + [None] * \
        (total_auto_neg_len - 4),  # 26  -70
        none,  # 27
        [None] * (4 + len(auto_neg_items)) + bids + [None] * \
        (total_auto_neg_len - 8 - len(auto_neg_items)),  # 28 - 70
        [None] * (4 + len(auto_neg_items) + 4) + list(keyword_negatives) + list(phrases_negatives),  # 29 - 70
        [None] * (4 + len(auto_neg_items) + 4) + ['negativeExact'] * len(keyword_negatives) + ['negativePhrase'] * len(phrases_negatives),  # 30 - 70 tuuuuuuuuuuuuut
        ['Dynamic bids - down only'] * 3 + [None] * \
        (total_auto_neg_len - 3),  # 31 - 70 tiuuuuuuuuuuuuuuuuuuuut
        [None, 'placementProductPage', 'placementTop'] + \
        [None] * (total_auto_neg_len - 3),  # 32 - 70
        [None, 0, 0] + [None] * (total_auto_neg_len - 3),  # 33 - 70
        [None] * (4 + len(auto_neg_items)) + ['close-match', 'loose-match', 'substitutes',
                                              'complements'] + [None] * (total_auto_neg_len - 8 - len(auto_neg_items)),  # 34?
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_auto_all(auto_total_data, target_asin, pte):
    global cmp_ending
    auto_data = auto_total_data[:4]
    auto_items = [x.strip() for x in auto_data[2].split(',')]
    total_auto_len = 4 + len(auto_items) + 4
    index_of_enabled = pte.index('enabled')
    bids = ['', '', '', '']
    bids[index_of_enabled] = auto_data[-1]

    title = create_company_name(auto_total_data)

    none = [None] * total_auto_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_auto_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] +
        ['Product Ad'] * len(auto_items) + ['Product Targeting'] * 4,
        ['Create'] * total_auto_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_auto_len,
        [None] * 3 + [auto_data[1]] * (total_auto_len - 3),  #this
        none, none, none, none,
        [title[0] + target_asin + f' {cmp_ending}'] + [None] * (total_auto_len - 1),
        [None] * 3 + [auto_data[1]] + [None] * (len(auto_items) + 4),
        none,
        [None] * 3 + [auto_data[1]] * (total_auto_len - 3), #this
        none,
        [str(date.today()).replace('-', '')] + [None] * (total_auto_len - 1),
        none,
        ['AUTO'] + [None] * (total_auto_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (len(auto_items) + 1) + pte,
        ['enabled'] * total_auto_len,
        [None] * 3 + ['enabled'] * (1 + len(auto_items)) + [None] * 4,
        [300] + [None] * (total_auto_len - 1),
        [None] * 4 + auto_items + [None] * 4,
        none,
        [None] * 4 + ['Eligible'] * len(auto_items) + [None] * 4,
        none,
        [None] * 3 + [auto_data[-1]] + [None] * len(auto_items) + [None] * 4,
        none,
        [None] * (4 + len(auto_items)) + bids + [None] *
        (total_auto_len - 8 - len(auto_items)),  # 28 - 70
        none, none,
        ['Dynamic bids - down only'] * 3 + [None] * (total_auto_len - 3),
        [None, 'placementProductPage', 'placementTop'] + \
        [None] * (total_auto_len - 3),
        [None, 0, 0] + [None] * (total_auto_len - 3),
        [None] * (4 + len(auto_items)) + ['close-match',
                                          'loose-match', 'substitutes', 'complements'],
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_exact_part(exact_data, words_part, number='', remove_campaign=0, target_asin=''):
    global cmp_ending
    # print(f"words_part: {words_part}")
    exact_items = [x.strip() for x in exact_data[2].split(',')]
    total_exact_len = 4 + len(exact_items) + len(words_part)
    title = create_company_name(exact_data)
    # print(f"title i nmake_exact_partmake_exact_part: {title}")

    none = [None] * total_exact_len
    keyword = 'Product targeting' if 'PAT' in exact_data[0] else 'Keyword'
    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_exact_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(exact_items) +
        [keyword] * len(words_part),
        ['Create'] * total_exact_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_exact_len,
        [None] * 3 + [exact_data[1] + number] *
        (total_exact_len - 3), none, none, none, none,
        [title[0] + target_asin + f' {cmp_ending}'] +
        [None] * (total_exact_len - 1),
        [None] * 3 + [exact_data[1] + number] +
        [None] * (total_exact_len - 4), none,
        [None] * 3 + [exact_data[1] + number] * (total_exact_len - 3), none,
        [str(date.today()).replace('-', '')] +
        [None] * (total_exact_len - 1), none,
        ['MANUAL'] + [None] * (total_exact_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_exact_len - 3),
        ['enabled'] * total_exact_len,
        [None] * 3 + ['enabled'] * (total_exact_len - 3),
        [300] + [None] * (total_exact_len - 1),
        [None] * 4 + exact_items + [None] * len(words_part), none,
        [None] * 4 + ['Eligible'] *
        len(exact_items) + [None] * len(words_part), none,
        [None] * 3 + [exact_data[-1]] + [None] * (total_exact_len - 4), none,
        [None] * (total_exact_len - len(words_part)) +
        [exact_data[-1]] * len(words_part),
        [None] * (total_exact_len - len(words_part)) + list(words_part),
        [None] * (total_exact_len - len(words_part)) +
        ['exact'] * len(words_part),
        ['Dynamic bids - down only'] * 3 + [None] * (total_exact_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_exact_len - 3),
        [None, 0, 0] + [None] * (total_exact_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_exact_all(exact_total_data, remove_campaign, target_asin):
    # print(f"exact_total_data:{exact_total_data}")
    exact_data = exact_total_data[:4]
    exact_words = [x for x in exact_total_data[4:]
                   if x is not None and x != '']

    exact_words_parts = []
    while True:
        # print(f"tut_exact_words {exact_words}")
        exact_words_parts.append(exact_words[:300])
        exact_words = exact_words[300:]
        if len(exact_words) == 0:
            break

    all_exact_dfs = []

    for p, part in enumerate(exact_words_parts):
        if len(exact_words_parts) == 1:
            cur_df = make_exact_part(
                exact_data, part, remove_campaign=remove_campaign, target_asin=target_asin)
        elif p > 0:
            cur_df = make_exact_part(
                exact_data, part, str(p + 1), remove_campaign=3, target_asin=target_asin)
        else:
            cur_df = make_exact_part(exact_data, part, str(
                p + 1), remove_campaign=remove_campaign, target_asin=target_asin)
        all_exact_dfs.append(cur_df)       

    return pd.concat(all_exact_dfs).reset_index().drop('index', axis=1)


def make_exact_all_list(exact_total_data_list, target_asin):
    # print(f"exact_total_data_list: {exact_total_data_list}")
    exact_data_sorted = sorted([tuple(x) for x in exact_total_data_list])
    all_exact_lists_dfs = []                    
    # print(f"exact_data_sorted: {exact_data_sorted}")
    for i, k in enumerate(exact_data_sorted):
        if i == 0 or k[0] != exact_data_sorted[i - 1][0]:
            cur_df = make_exact_all(k, 0, target_asin)              
        else:
            cur_df = make_exact_all(k, 3, target_asin)
        all_exact_lists_dfs.append(cur_df)

    return pd.concat(all_exact_lists_dfs).reset_index().drop('index', axis=1)


def make_pat_all(exact_total_data, remove_campaign, target_asin):
    exact_data = exact_total_data[:4]
    exact_words = [x for x in exact_total_data[4:]
                   if x is not None and x != '']

    exact_words_parts = []
    while True:
        # print(f"tut exact_words_parts {exact_words}")
        exact_words_parts.append(exact_words[:300])
        exact_words = exact_words[300:]
        if len(exact_words) == 0:
            break

    all_exact_dfs = []
    pat_words = []
    for p, part in enumerate(exact_words_parts):
        if len(exact_words_parts) == 1:
            w, cur_df = make_pat_part(
                exact_data, part, target_asin, remove_campaign=remove_campaign)
        elif p > 0:
            w, cur_df = make_pat_part(
                exact_data, part, target_asin, str(p + 1), remove_campaign=3)
        else:
            w, cur_df = make_pat_part(exact_data, part, target_asin, str(
                p + 1), remove_campaign=remove_campaign)
        all_exact_dfs.append(cur_df)
        pat_words += pat_words

    return pat_words, pd.concat(all_exact_dfs).reset_index().drop('index', axis=1)


def make_pat_part(pat_data, part, target_asin, number='', remove_campaign=0):
    global cmp_ending
    pat_items = [x.strip() for x in pat_data[2].split(',')]
    pat_words = ['asin="' + x + '"' for x in part if x is not None and x != '']
    total_pat_len = 4 + len(pat_items) + len(pat_words)

    # print(f"pat_data: {pat_data}")
    title = create_company_name(pat_data)
    # print(f"title: {title}")

    none = [None] * total_pat_len

    return pat_words, pd.DataFrame(np.array([
        ['Sponsored Products'] * total_pat_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(pat_items) + [
            'Product targeting'] * len(pat_words),
        ['Create'] * total_pat_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_pat_len,
        [None] * 3 + [pat_data[1] + number] *
        (total_pat_len - 3), none, none, none, none,
        [title[0] + target_asin +
            f' {cmp_ending}'] + [None] * (total_pat_len - 1),
        [None] * 3 + [pat_data[1] + number] +
        [None] * (total_pat_len - 4), none,
        [None] * 3 + [pat_data[1] + number] * (total_pat_len - 3), none,
        [str(date.today()).replace('-', '')] +
        [None] * (total_pat_len - 1), none,
        ['MANUAL'] + [None] * (total_pat_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_pat_len - 3),
        ['enabled'] * total_pat_len,
        [None] * 3 + ['enabled'] * (total_pat_len - 3),
        [300] + [None] * (total_pat_len - 1),
        [None] * 4 + pat_items + [None] * len(pat_words), none,
        [None] * 4 + ['Eligible'] *
        len(pat_items) + [None] * len(pat_words), none,
        [None] * 3 + [pat_data[-1]] + [None] * (total_pat_len - 4), none,
        [None] * (total_pat_len - len(pat_words)) +
        [pat_data[-1]] * len(pat_words), none,
        [None] * (total_pat_len - len(pat_words)) + ['exact'] * len(pat_words),
        ['Dynamic bids - down only'] * 3 + [None] * (total_pat_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_pat_len - 3),
        [None, 0, 0] + [None] * (total_pat_len - 3),
        [None] * (total_pat_len - len(pat_words)) + list(pat_words),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_pat_all_list(pat_total_data, target_asin, first_group=True):
    pat_data_sorted = sorted([tuple(x) for x in pat_total_data])
    all_pat_lists_dfs = []
    all_pat_words = []
    if first_group:
        for i, k in enumerate(pat_data_sorted):
            if i == 0 or k[0] != pat_data_sorted[i - 1][0]:
                cur_pat, cur_df = make_pat_all(k, 0, target_asin)
            else:
                cur_pat, cur_df = make_pat_all(k, 3, target_asin)
            all_pat_words.extend(cur_pat)
            all_pat_lists_dfs.append(cur_df)

    return all_pat_words, pd.concat(all_pat_lists_dfs).reset_index().drop('index', axis=1)


def make_category_all(category_total_data, pat_words, remove_campaign, target_asin):
    global cmp_ending
    category_data = category_total_data[:4]
    category_items = [x.strip() for x in category_data[2].split(',')]
    category_words = ['category="' + x +
                      '"' for x in category_total_data[4:] if x is not None and x != '']
    total_category_len = 4 + len(category_items) + \
        len(category_words) + len(pat_words)

    title = create_company_name(category_total_data)

    none = [None] * total_category_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_category_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(category_items) + [
            'Product targeting'] * len(category_words) + ['Negative Product Targeting'] * len(pat_words),
        ['Create'] * total_category_len,
        [title[0] + target_asin + f' {cmp_ending}'] * total_category_len,
        [None] * 3 + [category_data[1]] *
        (total_category_len - 3), none, none, none, none,
        [title[0] + target_asin + f' {cmp_ending}'] +
        [None] * (total_category_len - 1),
        [None] * 3 + [category_data[1]] + [None] *
        (total_category_len - 4), none,
        [None] * 3 + [category_data[1]] * (total_category_len - 3), none,
        [str(date.today()).replace('-', '')] +
        [None] * (total_category_len - 1), none,
        ['MANUAL'] + [None] * (total_category_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_category_len - 3),
        ['enabled'] * total_category_len,
        [None] * 3 + ['enabled'] * (total_category_len - 3),
        [300] + [None] * (total_category_len - 1),
        [None] * 4 + category_items + [None] *
        (len(category_words) + len(pat_words)), none,
        [None] * 4 + ['Eligible'] *
        len(category_items) + [None] *
        (len(category_words) + len(pat_words)), none,
        [None] * 3 + [category_data[-1]] +
        [None] * (total_category_len - 4), none,
        [None] * (total_category_len - len(category_words) - len(pat_words)) + [category_data[-1]] * len(
            category_words) + [None] * len(pat_words), 
        none,
        none,
        ['Dynamic bids - down only'] * 3 + [None] * (total_category_len - 3),
        [None, 'placementProductPage', 'placementTop'] +
        [None] * (total_category_len - 3),
        [None, 0, 0] + [None] * (total_category_len - 3),
        [None] * (total_category_len - len(category_words) -
                  len(pat_words)) + list(category_words) + list(pat_words),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_category_all_list(category_total_data_list, pat_words, target_asin):
    category_data_sorted = sorted([tuple(x) for x in category_total_data_list])
    all_category_lists_dfs = []
    for i, k in enumerate(category_data_sorted):
        if i == 0 or k[0] != category_data_sorted[i - 1][0]:
            cur_df = make_category_all(k, pat_words, 0, target_asin)
        else:
            cur_df = make_category_all(k, pat_words, 1, target_asin)
        all_category_lists_dfs.append(cur_df)

    return pd.concat(all_category_lists_dfs).reset_index().drop('index', axis=1)


def get_table_id(table_link):
    return table_link.split('/d/')[1].split('/')[0]


def sort_pats(pats_array):
    result_pats = [[] for _ in range(10)]
    for pat_company in pats_array:
        pat_header = list(pat_company)[0:4]
        pat_body = [e for e in list(pat_company) if e][4:]
        pat_header[1] = f'{pat_header[1]} '
        counter = 0
        while True:
            if len(pat_body):
                # print(f"tut {pat_body}")
                pats = pat_body[:300]
                pat_body = pat_body[300:]

                pat_header[1] = f'{pat_header[1][:-1]}{counter + 1}'
                result_pats[counter].append(pat_header + pats)
                counter += 1
            else:
                break

    return [np.array(pat, dtype=object) for pat in result_pats if len(pat)]


def google_sheets_bulk(table_link, campaign_data, cmp_end, campaign_2_data):
    global cmp_ending
    cmp_ending = cmp_end
    if len(sys.argv) < 2:
        print('No spreadsheet_id provided')
        sys.exit()
    keywords = []
    seed = []
    launched = []
    str_low = []

    SPREADSHEET_ID = get_table_id(table_link)
    gc = gspread.service_account(filename='amazon/apikey.json')
    sht1 = gc.open_by_key(SPREADSHEET_ID)

    range_name = None

    worksheet_objs = sht1.worksheets()
    range_name_general = sht1.sheet1.title
    df_total_general = get_data_frame(
        API_KEY, SPREADSHEET_ID, range_name_general)
    for worksheet in worksheet_objs:
        if 'clusters' in worksheet.title.lower():
            range_name = worksheet.title
            # print(f"range_name: {range_name}")

    for k in df_total_general.T.values:
        # if k[0].lower() == 'launched':
        #     launched = [x for x in k[1:] if x is not None and x != '']
        # elif k[0].lower() == 'seed':
        #     seed = [x for x in k[1:] if x is not None and x !=
        #             '' and x not in launched]
        if k[0].lower() == 'keywords':
            keywords = [x for x in k[1:]
                        if x is not None and x != '' and x not in launched]
        # elif k[0].lower() == 'str low':
        #     str_low = [x for x in k[1:] if x is not None and x !=
        #                '' and x not in launched]
    keyword_negatives = keywords

    df_total = get_data_frame(API_KEY, SPREADSHEET_ID, range_name)
    df_cols_needed = df_total[:1].values[0]
    df_negatives_needed = df_total[1:]
    df_negatives_needed.columns = df_cols_needed
    keyword_neg = None
    phrase_neg = None
    phrases_negatives = []
    for k in df_cols_needed:
        if k is None:
            continue
        if 'negativeexacts' in k.lower():
            keyword_neg = k
        elif 'phrase' in k.lower():
            phrase_neg = k
    if phrase_neg is not None:
        phrases_negatives = [x for x in df_negatives_needed[phrase_neg][5:] if x]
    # print(f"keyword_negatives: {keyword_negatives}")
    filter_campaign_name_snake_case = ""
    tos = []
    seed_total_data = []
    keyword_negatives_list = keyword_negatives.copy()
    broad_total_data = []
    words_total_data = []
    auto_close_neg_total_data = []
    auto_close_total_data = []
    auto_loose_neg_total_data = []
    auto_loose_total_data = []
    auto_subs_neg_total_data = []
    auto_subs_total_data = []
    auto_compl_neg_total_data = []
    auto_compl_total_data = []
    exact_total_data_list = []
    pat_total_data_list = []
    category_total_data_list = []
    brands_total_data_list = []
    variations_total_data_list = []
    brand_defense_list = []
    advertised_asins_list = []

    # print(f"campaign_data: {campaign_data}")
    for index, k in enumerate(df_total.values.T):
        # print(f"keyword_negatives: {keyword_negatives}")
        k = k.tolist()
        # print(f"k:{k}")
        k_head = k[:5]
        # print(f"k\k_head:{k_head}")

        k_tail = [x for x in k[5:] if x is not None and x != '']
        # print(f"k\k_tail:{k_tail}")

        k = k_head + k_tail
        if not k:
            # print(f"not k in k info: {k}")
            continue

        if k[0] == 'Advertised ASIN':                                               
            advertised_asins_list.append(k[1:])
        if k[1] and k[1] != ' ':
            filter_campaign_name = extract_text(k[1])
            filter_campaign_name_snake_case = to_snake_case(
                filter_campaign_name)
            # print(f"we in cheker: {filter_campaign_name_snake_case}")                                      
            print(
                f"filter_campaign_name_snake_case: {filter_campaign_name_snake_case}")
            print(f"campaign_data: {campaign_data}")
            # print(f"campaign_2_data: {campaign_2_data}")

            if filter_campaign_name_snake_case not in campaign_data:
                if k[0].lower() not in campaign_2_data:
                    print(f"LOSE IT: {filter_campaign_name_snake_case}; k[0]: {k[0]}")
                    continue
        if k[0] == 'SEED':
            seed_total_data.append(k[1:])
            tos.append(df_total.values.T[index+2][4])
            # keyword_negatives_list.append(k[5:])
            if len(keyword_negatives) > 0:
                keyword_negatives_set = set(keyword_negatives_list)
                for item in k[5:]:
                    if item not in keyword_negatives_set:
                        keyword_negatives_set.add(item)
                keyword_negatives_list = [list(keyword_negatives_set)]
            else: 
                keyword_negatives_list.append(k[5:])
            print("Seed Finished get seed")
        if k[0] == 'Brand Defense':
            brand_defense_list.append(k[1:])
        if k[0] == 'Broad':
            # print(f"broad this: {k}")
            broad_total_data.append(k[1:])
            # print(f"broad_total_data: {broad_total_data}")
        if k[0] == 'Words':
            words_total_data.append(k[1:])
        if 'Variation' in k[0]:
            variations_total_data_list.append(k[1:])
        if k[0] == 'Auto' and 'Negative' in k[1]:
            if 'Close' in k[1]:
                auto_close_neg_total_data.append(k[1:])
            elif 'Loose' in k[1]:
                auto_loose_neg_total_data.append(k[1:])
            elif 'Subs' in k[1]:
                auto_subs_neg_total_data.append(k[1:])
            else:
                auto_compl_neg_total_data.append(k[1:])
        if k[0] == 'Auto' and 'Negative' not in k[1]:
            if 'Close' in k[1]:
                auto_close_total_data.append(k[1:])
            elif 'Loose' in k[1]:
                auto_loose_total_data.append(k[1:])
            elif 'Subs' in k[1]:
                auto_subs_total_data.append(k[1:])
            else:
                auto_compl_total_data.append(k[1:])
        if k[0] == 'Brands':
            if any(k[5:]):
                brands_total_data_list.append(k[1:])
        if k[0] == 'Exact':
            if any(k[5:]):
                exact_total_data_list.append(k[1:])
        if k[0] == 'PAT':
            if any(k[5:]):
                pat_total_data_list.append(k[1:])
        if k[0] == 'Category':
            if any(k[5:]):
                category_total_data_list.append(k[1:])
        
    print("Finished get info")
    table_create_params = []

# d---------------------------------------------------------------------------------------------------------------
    # data: ["Advertised ASIN", "galon clear jojoba oil ", "Brand Defense", "bid(seed)"]

    if len(brand_defense_list) > 0 and len(brand_defense_list) > 0:
        for brand_defense_list_item in brand_defense_list:
            if len(brand_defense_list_item) > 4 and any(brand_defense_list_item[4]):
                data = [brand_defense_list_item[2], brand_defense_list_item[0].split(
                    "(")[0], "Brand Defense", brand_defense_list_item[3]]
                brand_defense_all = make_brand_def_all(                                                          
                    brand_defense_list_item[4:], data)
                table_create_params.append(brand_defense_all)

    if len(advertised_asins_list) > 0 and len(brand_defense_list) > 0:
        for advertised_asins_list_item in advertised_asins_list:
            if len(advertised_asins_list_item) > 0 and len(brand_defense_list) > 0 and any(brand_defense_list[0][3]):
                data = [[advertised_asins_list_item[4]], advertised_asins_list_item[0].split(
                    "(")[0], "Advertised ASIN", brand_defense_list[0][3], [advertised_asins_list_item[2]]]
                our_adv_asins_all = make_brand_advertised_asins(data)
                table_create_params.append(our_adv_asins_all)
# d---------------------------------------------------------------------------------------------------------------
    if len(variations_total_data_list) > 0:
            variations_all = make_exact_all_list(
                variations_total_data_list, advertised_asins_list[0][4])
            table_create_params.append(variations_all)

    # if len(seed_total_data) > 0:
    #     for seed_total_data_item in seed_total_data:
    #         if any(seed_total_data_item[4:]) and seed_total_data_item[2]:
    #             seed_all = make_seed_all(seed_total_data_item, tar    get_asin)
    #             table_create_params.append(seed_all)
    if len(seed_total_data) > 0 and len(tos) > 0:                                            
        for seed_total_data_item, tos_item, target_asin in zip(seed_total_data, tos, advertised_asins_list):
            if tos_item == '' or tos_item == ' ':
                tos_item = 0
            if any(seed_total_data_item[4:]) and seed_total_data_item[2]:
                seed_all = make_seed_all(
                    seed_total_data_item, target_asin[4], tos_item)
                table_create_params.append(seed_all)

    if len(broad_total_data) > 0:
        i = 1
        if len(advertised_asins_list) < len(broad_total_data):
            advertised_asins_list_prime = [advertised_asins_list[0]] * len(broad_total_data)
        else:
            advertised_asins_list_prime = advertised_asins_list
        # print(f"keyword_negatives_list: {keyword_negatives_list}")
        # print(f"len(keyword_negatives_list): {len(keyword_negatives_list)}; len(broad_total_data): {len(broad_total_data)}")
        if len(keyword_negatives_list) < len(broad_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(broad_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        # print(f"keyword_negatives_list_prime: {keyword_negatives_list_prime}")
        for broad_total_data_item, keyword_negatives, target_asin in zip(broad_total_data, keyword_negatives_list_prime, advertised_asins_list_prime):
            if any(broad_total_data_item[4:]):
                broad_all = make_broad_all(
                    broad_total_data_item, keyword_negatives, phrases_negatives, target_asin[4])
                table_create_params.append(broad_all)
            i+=1

    if len(words_total_data) > 0:
        if len(keyword_negatives_list) < len(words_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(words_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        # print(f"keyword_negatives_list: {keyword_negatives_list}")
        # print(f"keyword_negatives_list_prime: {keyword_negatives_list_prime}")

        for words_total_data_item, keyword_negatives, target_asin in zip(words_total_data, keyword_negatives_list_prime, advertised_asins_list):
            # print(f"keyword_negatives: {keyword_negatives}")
            if any(words_total_data_item[4:]):
                words_all = make_broad_all(
                    words_total_data_item, keyword_negatives, phrases_negatives, target_asin[4])
                table_create_params.append(words_all)

    if len(auto_close_neg_total_data) > 0:
        if len(keyword_negatives_list) < len(auto_close_neg_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(auto_close_neg_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        for auto_close_neg_total_data_item, keyword_negatives, target_asin in zip(auto_close_neg_total_data, keyword_negatives_list_prime, advertised_asins_list):
            if len(auto_close_neg_total_data_item):
                auto_close_neg_all = make_auto_neg_all(
                    auto_close_neg_total_data_item, keyword_negatives, phrases_negatives, target_asin[4], ['enabled', 'paused', 'paused', 'paused'])
                table_create_params.append(auto_close_neg_all)

    if len(auto_close_total_data) > 0:
        for auto_close_total_data_item, target_asin in zip(auto_close_total_data, advertised_asins_list):
            if len(auto_close_total_data_item):
                auto_close_all = make_auto_all(auto_close_total_data_item, target_asin[4], [
                                            'enabled', 'paused', 'paused', 'paused'])
                table_create_params.append(auto_close_all)

    if len(auto_loose_neg_total_data) > 0:                                                                                                 
        if len(keyword_negatives_list) < len(auto_loose_neg_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(auto_loose_neg_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        for auto_loose_neg_total_data_item, keyword_negatives, target_asin in zip(auto_loose_neg_total_data, keyword_negatives_list_prime, advertised_asins_list):
            if len(auto_loose_neg_total_data_item):
                auto_loose_neg_all = make_auto_neg_all(
                    auto_loose_neg_total_data_item, keyword_negatives, phrases_negatives, target_asin[4], ['paused', 'enabled', 'paused', 'paused'])
                table_create_params.append(auto_loose_neg_all)

    if len(auto_loose_total_data) > 0:
        for auto_loose_total_data_item, target_asin in zip(auto_loose_total_data, advertised_asins_list):
            if len(auto_loose_total_data_item):
                auto_loose_all = make_auto_all(auto_loose_total_data_item, target_asin[4], [
                                            'paused', 'enabled', 'paused', 'paused'])
                table_create_params.append(auto_loose_all)

    if len(auto_subs_neg_total_data) > 0:
        if len(keyword_negatives_list) < len(auto_subs_neg_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(auto_subs_neg_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        for auto_subs_neg_total_data_item, keyword_negatives, target_asin in zip(auto_subs_neg_total_data, keyword_negatives_list_prime, advertised_asins_list):
            if len(auto_subs_neg_total_data_item):
                auto_subs_neg_all = make_auto_neg_all(
                    auto_subs_neg_total_data_item, keyword_negatives, phrases_negatives, target_asin[4], ['paused', 'paused', 'enabled', 'paused'])
                table_create_params.append(auto_subs_neg_all)

    if len(auto_subs_total_data) > 0:
        for auto_subs_total_data_item, target_asin in zip(auto_subs_total_data, advertised_asins_list):
            if len(auto_subs_total_data_item):
                auto_subs_all = make_auto_all(auto_subs_total_data_item, target_asin[4], [
                                            'paused', 'paused', 'enabled', 'paused'])
                table_create_params.append(auto_subs_all)

    if len(auto_compl_neg_total_data) > 0:
        if len(keyword_negatives_list) < len(auto_compl_neg_total_data):
            keyword_negatives_list_prime = [keyword_negatives_list[0]] * len(auto_compl_neg_total_data)
        else:
            keyword_negatives_list_prime = keyword_negatives_list
        for auto_compl_neg_total_data_item, keyword_negatives, target_asin in zip(auto_compl_neg_total_data, keyword_negatives_list_prime, advertised_asins_list):
            if len(auto_compl_neg_total_data_item):
                auto_compl_neg_all = make_auto_neg_all(
                    auto_compl_neg_total_data_item, keyword_negatives, phrases_negatives, target_asin[4], ['paused', 'paused', 'paused', 'enabled'])
                table_create_params.append(auto_compl_neg_all)

    if len(auto_compl_total_data) > 0:
        for auto_compl_total_data_item, target_asin in zip(auto_compl_total_data, advertised_asins_list):
            if len(auto_compl_total_data_item):
                auto_compl_all = make_auto_all(auto_compl_total_data_item, target_asin[4], [
                                            'paused', 'paused', 'paused', 'enabled'])
                table_create_params.append(auto_compl_all)

    if len(exact_total_data_list) > 0:
        exact_all = make_exact_all_list(
            exact_total_data_list, advertised_asins_list[0][4])
        table_create_params.append(exact_all)

    if len(brands_total_data_list) > 0:
        brands_all = make_exact_all_list(
            brands_total_data_list, advertised_asins_list[0][4])
        table_create_params.append(brands_all)

    if len(pat_total_data_list) > 0:
        pat_all = make_pat_all_list(
            pat_total_data_list, advertised_asins_list[0][4])[1]
        table_create_params.append(pat_all)

    if len(category_total_data_list) > 0:
        try:
            pat_words, pat_all = make_pat_all_list(
                pat_total_data_list, advertised_asins_list[0][4])
        except ValueError:
            pat_words = []
        category_all = make_category_all_list(
            category_total_data_list, pat_words, advertised_asins_list[0][4])
        table_create_params.append(category_all)

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Finished UPLOAD info to table_create_params{dt}")

    table_name = f'{range_name.replace("clusters", "bulk")}'
    worksheets_list = [worksheet.title for worksheet in sht1.worksheets()]

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Received worksheets_list:{worksheets_list} - {dt}")
    if f'{range_name.replace("clusters", "bulk")}' not in worksheets_list:
        sht1.add_worksheet(title=table_name, rows=100, cols=20)
        print(f"Create new list - {dt}")
    output_file_name = f'{range_name.replace("clusters", "bulk")}.xlsx'

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"cREATE output_file_name: {output_file_name} - {dt}")
    pd.concat(table_create_params).reset_index().drop('index', axis=1).to_excel(
        f'{MEDIA_ROOT}{output_file_name}', index=False)
    
    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Finished upload to excel - {dt}")
    read_file = pd.read_excel(f'{MEDIA_ROOT}{output_file_name}')

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Finished read filr from excel - {dt}")
    read_file.to_csv(f'{MEDIA_ROOT}{table_name}.csv', index=False, header=True)

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Finished upload to csv - {dt}")

    rows, cols = read_file.shape

    sqr_pd = int(rows) * int(cols)

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"sqr_pd 1: {sqr_pd} - {dt}")

    if sqr_pd > 9999999:
        split_and_upload_large_file(table_name, sht1, ['part_1', 'part_2']) 
    else:
        sht1.values_update(
        table_name,
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': list(csv.reader(open(f'media/{table_name}.csv')))}
    )

    return output_file_name

def split_and_upload_large_file(table_name, sht1, endings):

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Start split_and_upload_large_file - {dt}")
    df = pd.read_csv(f'media/{table_name}.csv')

    sht1.add_worksheet(title=f"{table_name}_{endings[0]}", rows=100, cols=20)
    sht1.add_worksheet(title=f"{table_name}_{endings[1]}", rows=100, cols=20)
    
    df_sorted = df.sort_values(df.columns[3]).reset_index(drop=True)
    
    mid_index = len(df_sorted) // 2
    
    middle_value = df_sorted.iloc[mid_index, 3]
    
    split_index = mid_index
    for i in range(mid_index, 0, -1):
        if df_sorted.iloc[i, 3] != middle_value:
            split_index = i
            break
    
    df_part1 = df_sorted.iloc[:split_index+1]
    df_part2 = df_sorted.iloc[split_index+1:]
    
    df_part1.to_csv(f'media/{table_name}_{endings[0]}.csv', index=False)
    df_part2.to_csv(f'media/{table_name}_{endings[1]}.csv', index=False)

    rows, cols = df_part1.shape
    sqr_pd = int(rows) * int(cols)

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"sqr_pd 2: {sqr_pd} - {dt}")

    if sqr_pd > 9999999:
        split_and_upload_large_file(f"{table_name}_{endings[0]}", sht1, ['part_3', 'part_4']) 
    else:
        sht1.values_update(
        f"{table_name}_{endings[0]}",
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': list(csv.reader(open(f'media/{table_name}_{endings[0]}.csv')))}
    )
    
    rows, cols = df_part2.shape
    sqr_pd = int(rows) * int(cols)

    dt = datetime.now().strftime("%H:%M:%S")
    print(f"sqr_pd 3: {sqr_pd} - {dt}")

    if sqr_pd > 9999999:
        split_and_upload_large_file(f"{table_name}_{endings[1]}", sht1, ['part_5', 'part_6']) 
    else:
        sht1.values_update(
        f"{table_name}_{endings[1]}",
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': list(csv.reader(open(f'media/{table_name}_{endings[1]}.csv')))}
    )
    
    dt = datetime.now().strftime("%H:%M:%S")
    print(f"Finish split_and_upload_large_file - {dt}")
               


def extract_text(input_string):
    # Перший випадок: "Team Cards | SEED" - повертаємо "SEED"
    match = re.search(r'\|\s*([A-Z]+)$', input_string)
    if match:
        return match.group(1)

    # Другий випадок: "Team Cards | PAT - RA" - повертаємо "PAT | RA"
    match = re.search(r'\|\s*([A-Z]+)\s*-\s*([A-Z]+)', input_string)
    if match:
        return f"{match.group(1)} | {match.group(2)}"

    # Третій випадок: Витягнути все після "|"
    match = re.search(r'\|\s*(.+?)\s*\d*$', input_string)
    if match:
        return match.group(1).strip()

    return None


def to_snake_case(name):
    new_name = name.lower()
    new_name = re.sub(r'\s+', '_', new_name)
    # print(f"new_name 1: {new_name}")
    # new_name = new_name.replace('-', '|')
    # print(f"new_name 2: {new_name}")
    new_name = new_name.strip('_')
    # print(f"name before: {name} <-> name after: {new_name}")
    return new_name
