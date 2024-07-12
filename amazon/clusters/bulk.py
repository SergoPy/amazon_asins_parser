import csv
import gspread
import pandas as pd
import numpy as np
import httplib2
import sys


from googleapiclient import discovery
from datetime import date

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


def get_data_frame(key, spreadsheet_id, range_name):
    discovery_url = ('https://sheets.googleapis.com/$discovery/rest?'
                     'version=v4')
    service = discovery.build(
        'sheets',
        'v4',
        http=httplib2.Http(),
        discoveryServiceUrl=discovery_url,
        developerKey=key)

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    return pd.DataFrame(values)


def make_tpk_one(tpk_data, word):
    tpk_items = [x.strip() for x in tpk_data[2].split(',') if x]
    total_tpk_len = 5 + len(tpk_items)

    none = [None] * total_tpk_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_tpk_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(tpk_items) + ['Keyword'],
        ['Create'] * total_tpk_len,
        [tpk_data[0] + ' - ' + word + ' -SP'] * total_tpk_len,
        [None] * 3 + [tpk_data[1]] * (total_tpk_len - 3), none, none, none, none,
        [tpk_data[0] + ' - ' + word + ' -SP'] + [None] * (total_tpk_len - 1),
        [None] * 3 + [tpk_data[1]] + [None] * (total_tpk_len - 4), none,
        [None] * 3 + [tpk_data[1]] * (total_tpk_len - 3), none,
        [str(date.today()).replace('-', '')] + [None] * (total_tpk_len - 1), none,
        ['MANUAL'] + [None] * (total_tpk_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_tpk_len - 3),
        ['enabled'] * total_tpk_len,
        [None] * 3 + ['enabled'] * (total_tpk_len - 3),
        [300] + [None] * (total_tpk_len - 1),
        [None] * 4 + tpk_items + [None], none,
        [None] * 4 + ['Eligible'] * len(tpk_items) + [None], none,
        [None] * 3 + [tpk_data[-1]] + [None] * (total_tpk_len - 4), none,
        [None] * (total_tpk_len - 1) + [tpk_data[-1]],
        [None] * (total_tpk_len - 1) + [word],
        [None] * (total_tpk_len - 1) + ['exact'],
        ['Dynamic bids - down only'] * 3 + [None] * (total_tpk_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_tpk_len - 3),
        [None, 0, 0] + [None] * (total_tpk_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_tpk_all(tpk_total_data):
    tpk_data = tpk_total_data[:4]
    tpk_words = [x for x in tpk_total_data[4:] if x]

    all_tpk_dfs = []
    for k in tpk_words:
        cur_df = make_tpk_one(tpk_data, k)
        all_tpk_dfs.append(cur_df)

    return pd.concat(all_tpk_dfs).reset_index().drop('index', axis=1)


def make_broad_all(broad_total_data, keyword_negatives, phrases_negatives):
    broad_data = broad_total_data[:4]
    broad_words = [x for x in broad_total_data[4:] if x is not None and x != '']
    try:
        broad_items = [x.strip() for x in broad_data[2].split(',') if x]
    except AttributeError:
        broad_items = []
    total_broad_len = 4 + len(broad_items) + len(broad_words) + len(keyword_negatives) + len(phrases_negatives)

    none = [None] * total_broad_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_broad_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(broad_items) + [
            'Keyword'] * len(broad_words) + \
        ['Campaign Negative Keyword'] * (len(keyword_negatives) + len(phrases_negatives)),
        ['Create'] * total_broad_len,
        [broad_data[0] + ' -SP'] * total_broad_len,
        [None] * 3 + [broad_data[1]] * (1 + len(broad_items) + len(broad_words)) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)),
        none, none, none, none,
        [broad_data[0] + ' -SP'] + [None] * (total_broad_len - 1),
        [None] * 3 + [broad_data[1]] + [None] * (total_broad_len - 4), none,
        [None] * 3 + [broad_data[1]] * (1 + len(broad_items) + len(broad_words)) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)), none,
        [str(date.today()).replace('-', '')] + [None] * (total_broad_len - 1), none,
        ['MANUAL'] + [None] * (total_broad_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_broad_len - 3),
        ['enabled'] * total_broad_len,
        [None] * 3 + ['enabled'] * (1 + len(broad_items) + len(broad_words)) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)),
        [300] + [None] * (total_broad_len - 1),
        [None] * 4 + broad_items + [None] * (total_broad_len - 4 - len(broad_items)), none,
        [None] * 4 + ['Eligible'] * len(broad_items) + [None] * (total_broad_len - 4 - len(broad_items)), none,
        [None] * 3 + [broad_data[-1]] * len(broad_items) + [None] * (total_broad_len - 3 - len(broad_items)), none,
        [None] * (4 + len(broad_items)) + [broad_data[-1]] * len(broad_words) + [None] * (
                len(keyword_negatives) + len(phrases_negatives)),
        [None] * (4 + len(broad_items)) + list(broad_words) + list(keyword_negatives) + list(phrases_negatives),
        [None] * (4 + len(broad_items)) + [broad_data[1]] * len(broad_words) + ['negativeExact'] * len(
            keyword_negatives) +
        ['negativePhrase'] * len(phrases_negatives),
        ['Dynamic bids - down only'] * 3 + [None] * (total_broad_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_broad_len - 3),
        [None, 0, 0] + [None] * (total_broad_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_auto_neg_all(auto_neg_total_data, keyword_negatives, phrases_negatives):
    auto_neg_data = auto_neg_total_data[:4]
    auto_neg_items = [x.strip() for x in auto_neg_data[2].split(',')]
    total_auto_neg_len = 4 + len(auto_neg_items) + len(keyword_negatives) + len(phrases_negatives)

    none = [None] * total_auto_neg_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_auto_neg_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(auto_neg_items) + \
        ['Campaign Negative Keyword'] * (len(keyword_negatives) + len(phrases_negatives)),
        ['Create'] * total_auto_neg_len,
        [auto_neg_data[0] + ' -SP'] * total_auto_neg_len,
        [None] * 3 + [auto_neg_data[1]] * (total_auto_neg_len - 3), none, none, none, none,
        [auto_neg_data[0] + ' -SP'] + [None] * (total_auto_neg_len - 1),
        [None] * 3 + [auto_neg_data[1]] + [None] * (total_auto_neg_len - 4), none,
        [None] * 3 + [auto_neg_data[1]] * (1 + len(auto_neg_items)) + \
        [None] * (total_auto_neg_len - 4 - len(auto_neg_items)), none,
        [str(date.today()).replace('-', '')] + [None] * (total_auto_neg_len - 1), none,
        ['AUTO'] + [None] * (total_auto_neg_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_auto_neg_len - 3),
        ['enabled'] * total_auto_neg_len,
        [None] * 3 + ['enabled'] * (1 + len(auto_neg_items)) + \
        [None] * (total_auto_neg_len - 4 - len(auto_neg_items)),
        [300] + [None] * (total_auto_neg_len - 1),
        [None] * 4 + auto_neg_items + [None] * (total_auto_neg_len - len(auto_neg_items) - 4), none,
        [None] * 4 + ['Eligible'] * len(auto_neg_items) + [None] * (total_auto_neg_len - 4 - len(auto_neg_items)),
        none, [None] * 3 + [auto_neg_data[-1]] + [None] * (total_auto_neg_len - 4), none, none,
        [None] * (4 + len(auto_neg_items)) + list(keyword_negatives) + list(phrases_negatives),
        [None] * (4 + len(auto_neg_items)) + ['negativeExact'] * len(keyword_negatives) + \
        ['negativePhrase'] * len(phrases_negatives),
        ['Dynamic bids - down only'] * 3 + [None] * (total_auto_neg_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_auto_neg_len - 3),
        [None, 0, 0] + [None] * (total_auto_neg_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_auto_all(auto_total_data):
    auto_data = auto_total_data[:4]
    auto_items = [x.strip() for x in auto_data[2].split(',')]
    total_auto_len = 4 + len(auto_items)

    none = [None] * total_auto_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_auto_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(auto_items),
        ['Create'] * total_auto_len,
        [auto_data[0] + ' -SP'] * total_auto_len,
        [None] * 3 + [auto_data[1]] * (total_auto_len - 3), none, none, none, none,
        [auto_data[0] + ' -SP'] + [None] * (total_auto_len - 1),
        [None] * 3 + [auto_data[1]] + [None] * len(auto_items), none,
        [None] * 3 + [auto_data[1]] * (1 + len(auto_items)), none,
        [str(date.today()).replace('-', '')] + [None] * (total_auto_len - 1), none,
        ['AUTO'] + [None] * (total_auto_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_auto_len - 3),
        ['enabled'] * total_auto_len,
        [None] * 3 + ['enabled'] * (1 + len(auto_items)),
        [300] + [None] * (total_auto_len - 1),
        [None] * 4 + auto_items, none,
        [None] * 4 + ['Eligible'] * len(auto_items), none,
        [None] * 3 + [auto_data[-1]] + [None] * len(auto_items), none, none, none, none,
        ['Dynamic bids - down only'] * 3 + [None] * (total_auto_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_auto_len - 3),
        [None, 0, 0] + [None] * (total_auto_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)


def make_exact_part(exact_data, words_part, number='', remove_campaign=0):
    exact_items = [x.strip() for x in exact_data[2].split(',')]
    total_exact_len = 4 + len(exact_items) + len(words_part)

    none = [None] * total_exact_len
    keyword = 'Product targeting' if 'PAT' in exact_data[0] else 'Keyword'
    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_exact_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(exact_items) + \
        [keyword] * len(words_part),
        ['Create'] * total_exact_len,
        [exact_data[0] + ' -SP'] * total_exact_len,
        [None] * 3 + [exact_data[1] + number] * (total_exact_len - 3), none, none, none, none,
        [exact_data[0] + ' -SP'] + [None] * (total_exact_len - 1),
        [None] * 3 + [exact_data[1] + number] + [None] * (total_exact_len - 4), none,
        [None] * 3 + [exact_data[1] + number] * (total_exact_len - 3), none,
        [str(date.today()).replace('-', '')] + [None] * (total_exact_len - 1), none,
        ['MANUAL'] + [None] * (total_exact_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_exact_len - 3),
        ['enabled'] * total_exact_len,
        [None] * 3 + ['enabled'] * (total_exact_len - 3),
        [300] + [None] * (total_exact_len - 1),
        [None] * 4 + exact_items + [None] * len(words_part), none,
        [None] * 4 + ['Eligible'] * len(exact_items) + [None] * len(words_part), none,
        [None] * 3 + [exact_data[-1]] + [None] * (total_exact_len - 4), none,
        [None] * (total_exact_len - len(words_part)) + [exact_data[-1]] * len(words_part),
        [None] * (total_exact_len - len(words_part)) + list(words_part),
        [None] * (total_exact_len - len(words_part)) + ['exact'] * len(words_part),
        ['Dynamic bids - down only'] * 3 + [None] * (total_exact_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_exact_len - 3),
        [None, 0, 0] + [None] * (total_exact_len - 3),
        none, none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_exact_all(exact_total_data, remove_campaign):
    exact_data = exact_total_data[:4]
    exact_words = [x for x in exact_total_data[4:] if x is not None and x != '']

    exact_words_parts = []
    while True:
        exact_words_parts.append(exact_words[:300])
        exact_words = exact_words[300:]
        if len(exact_words) == 0:
            break

    all_exact_dfs = []

    for p, part in enumerate(exact_words_parts):
        if len(exact_words_parts) == 1:
            cur_df = make_exact_part(exact_data, part, remove_campaign=remove_campaign)
        elif p > 0:
            cur_df = make_exact_part(exact_data, part, str(p + 1), remove_campaign=3)
        else:
            cur_df = make_exact_part(exact_data, part, str(p + 1), remove_campaign=remove_campaign)
        all_exact_dfs.append(cur_df)

    return pd.concat(all_exact_dfs).reset_index().drop('index', axis=1)


def make_exact_all_list(exact_total_data_list):
    exact_data_sorted = sorted([tuple(x) for x in exact_total_data_list])
    all_exact_lists_dfs = []
    for i, k in enumerate(exact_data_sorted):
        if i == 0 or k[0] != exact_data_sorted[i - 1][0]:
            cur_df = make_exact_all(k, 0)
        else:
            cur_df = make_exact_all(k, 3)
        all_exact_lists_dfs.append(cur_df)

    return pd.concat(all_exact_lists_dfs).reset_index().drop('index', axis=1)

def make_pat_all(exact_total_data, remove_campaign):
    exact_data = exact_total_data[:4]
    exact_words = [x for x in exact_total_data[4:] if x is not None and x != '']

    exact_words_parts = []
    while True:
        exact_words_parts.append(exact_words[:300])
        exact_words = exact_words[300:]
        if len(exact_words) == 0:
            break

    all_exact_dfs = []
    pat_words = []
    for p, part in enumerate(exact_words_parts):
        if len(exact_words_parts) == 1:
            w, cur_df = make_pat_part(exact_data, part, remove_campaign=remove_campaign)
        elif p > 0:
            w, cur_df = make_pat_part(exact_data, part, str(p + 1), remove_campaign=3)
        else:
            w, cur_df = make_pat_part(exact_data, part, str(p + 1), remove_campaign=remove_campaign)
        all_exact_dfs.append(cur_df)
        pat_words += pat_words

    return pat_words, pd.concat(all_exact_dfs).reset_index().drop('index', axis=1)

def make_pat_part(pat_data, part, number='', remove_campaign=0):
    pat_items = [x.strip() for x in pat_data[2].split(',')]
    pat_words = ['asin="' + x + '"' for x in part if x is not None and x != '']
    total_pat_len = 4 + len(pat_items) + len(pat_words)

    none = [None] * total_pat_len

    return pat_words, pd.DataFrame(np.array([
        ['Sponsored Products'] * total_pat_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(pat_items) + [
            'Product targeting'] * len(pat_words),
        ['Create'] * total_pat_len,
        [pat_data[0] + ' -SP'] * total_pat_len,
        [None] * 3 + [pat_data[1] + number] * (total_pat_len - 3), none, none, none, none,
        [pat_data[0] + ' -SP'] + [None] * (total_pat_len - 1),
        [None] * 3 + [pat_data[1] + number] + [None] * (total_pat_len - 4), none,
        [None] * 3 + [pat_data[1] + number] * (total_pat_len - 3), none,
        [str(date.today()).replace('-', '')] + [None] * (total_pat_len - 1), none,
        ['MANUAL'] + [None] * (total_pat_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_pat_len - 3),
        ['enabled'] * total_pat_len,
        [None] * 3 + ['enabled'] * (total_pat_len - 3),
        [300] + [None] * (total_pat_len - 1),
        [None] * 4 + pat_items + [None] * len(pat_words), none,
        [None] * 4 + ['Eligible'] * len(pat_items) + [None] * len(pat_words), none,
        [None] * 3 + [pat_data[-1]] + [None] * (total_pat_len - 4), none,
        [None] * (total_pat_len - len(pat_words)) + [pat_data[-1]] * len(pat_words), none,
        [None] * (total_pat_len - len(pat_words)) + ['exact'] * len(pat_words),
        ['Dynamic bids - down only'] * 3 + [None] * (total_pat_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_pat_len - 3),
        [None, 0, 0] + [None] * (total_pat_len - 3),
        [None] * (total_pat_len - len(pat_words)) + list(pat_words),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_pat_all_list(pat_total_data, first_group=True):
    pat_data_sorted = sorted([tuple(x) for x in pat_total_data])
    all_pat_lists_dfs = []
    all_pat_words = []
    if first_group:
        for i, k in enumerate(pat_data_sorted):
            if i == 0 or k[0] != pat_data_sorted[i - 1][0]:
                cur_pat, cur_df = make_pat_all(k, 0)
            else:
                cur_pat, cur_df = make_pat_all(k, 3)
            all_pat_words.extend(cur_pat)
            all_pat_lists_dfs.append(cur_df)

    return all_pat_words, pd.concat(all_pat_lists_dfs).reset_index().drop('index', axis=1)


def make_category_all(category_total_data, pat_words, remove_campaign):
    category_data = category_total_data[:4]
    category_items = [x.strip() for x in category_data[2].split(',')]
    category_words = ['category="' + x + '"' for x in category_total_data[4:] if x is not None and x != '']
    total_category_len = 4 + len(category_items) + len(category_words) + len(pat_words)

    none = [None] * total_category_len

    return pd.DataFrame(np.array([
        ['Sponsored Products'] * total_category_len,
        ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(category_items) + [
            'Product targeting'] * len(category_words) + ['Negative Product Targeting'] * len(pat_words),
        ['Create'] * total_category_len,
        [category_data[0] + ' -SP'] * total_category_len,
        [None] * 3 + [category_data[1]] * (total_category_len - 3), none, none, none, none,
        [category_data[0] + ' -SP'] + [None] * (total_category_len - 1),
        [None] * 3 + [category_data[1]] + [None] * (total_category_len - 4), none,
        [None] * 3 + [category_data[1]] * (total_category_len - 3), none,
        [str(date.today()).replace('-', '')] + [None] * (total_category_len - 1), none,
        ['MANUAL'] + [None] * (total_category_len - 1),
        ['enabled'] + [None] * 2 + ['enabled'] * (total_category_len - 3),
        ['enabled'] * total_category_len,
        [None] * 3 + ['enabled'] * (total_category_len - 3),
        [300] + [None] * (total_category_len - 1),
        [None] * 4 + category_items + [None] * (len(category_words) + len(pat_words)), none,
        [None] * 4 + ['Eligible'] * len(category_items) + [None] * (len(category_words) + len(pat_words)), none,
        [None] * 3 + [category_data[-1]] + [None] * (total_category_len - 4), none,
        [None] * (total_category_len - len(category_words) - len(pat_words)) + [category_data[-1]] * len(
            category_words) + [None] * len(pat_words), none,
        [None] * (total_category_len - len(category_words) - len(pat_words)) + ['exact'] * len(category_words) + [
            None] * len(pat_words),
        ['Dynamic bids - down only'] * 3 + [None] * (total_category_len - 3),
        [None, 'placementProductPage', 'placementTop'] + [None] * (total_category_len - 3),
        [None, 0, 0] + [None] * (total_category_len - 3),
        [None] * (total_category_len - len(category_words) - len(pat_words)) + list(category_words) + list(pat_words),
        none, none, none, none, none, none, none, none, none, none, none, none
    ]).T, columns=COLUMNS)[remove_campaign:]


def make_category_all_list(category_total_data_list, pat_words):
    category_data_sorted = sorted([tuple(x) for x in category_total_data_list])
    all_category_lists_dfs = []
    for i, k in enumerate(category_data_sorted):
        if i == 0 or k[0] != category_data_sorted[i - 1][0]:
            cur_df = make_category_all(k, pat_words, 0)
        else:
            cur_df = make_category_all(k, pat_words, 1)
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
                pats = pat_body[:300]
                pat_body = pat_body[300:]

                pat_header[1] = f'{pat_header[1][:-1]}{counter + 1}'
                result_pats[counter].append(pat_header + pats)
                counter += 1
            else:
                break

    return [np.array(pat, dtype=object) for pat in result_pats if len(pat)]


def google_sheets_bulk(table_link):
    if len(sys.argv) < 2:
        print('No spreadsheet_id provided')
        sys.exit()

    SPREADSHEET_ID = get_table_id(table_link)
    gc = gspread.service_account(filename='amazon/apikey.json')
    sht1 = gc.open_by_key(SPREADSHEET_ID)

    range_name = None

    worksheet_objs = sht1.worksheets()
    for worksheet in worksheet_objs:
        if 'clusters' in worksheet.title.lower():
            range_name = worksheet.title

    df_total = get_data_frame(API_KEY, SPREADSHEET_ID, range_name)
    df_cols_needed = df_total[:1].values[0]
    df_negatives_needed = df_total[1:]
    df_negatives_needed.columns = df_cols_needed
    keyword_neg = None
    phrase_neg = None
    for k in df_cols_needed:
        if 'negativeexacts' in k.lower():
            keyword_neg = k
        elif 'phrase' in k.lower():
            phrase_neg = k

    keyword_negatives = [x for x in df_negatives_needed[keyword_neg] if x]
    phrases_negatives = [x for x in df_negatives_needed[phrase_neg] if x]

    tpk_total_data = []
    broad_total_data = []
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

    for k in df_total.values.T:
        if k[0] == 'TPK':
            tpk_total_data = k[1:]
        elif k[0] == 'Broad':
            broad_total_data = k[1:]
        elif 'Variation' in k[0]:
            variations_total_data_list.append(k[1:])
        elif k[0] == 'Auto' and 'Negative' in k[1]:
            if 'Close' in k[1]:
                auto_close_neg_total_data = k[1:]
            elif 'Loose' in k[1]:
                auto_loose_neg_total_data = k[1:]
            elif 'Subs' in k[1]:
                auto_subs_neg_total_data = k[1:]
            else:
                auto_compl_neg_total_data = k[1:]
        elif k[0] == 'Auto':
            if 'Close' in k[1]:
                auto_close_total_data = k[1:]
            elif 'Loose' in k[1]:
                auto_loose_total_data = k[1:]
            elif 'Subs' in k[1]:
                auto_subs_total_data = k[1:]
            else:
                auto_compl_total_data = k[1:]
        elif k[0] == 'Brands':
            if any(k[5:]):
                brands_total_data_list.append(k[1:])
        elif k[0] == 'Exact':
            if any(k[5:]):
                exact_total_data_list.append(k[1:])
        elif k[0] == 'PAT':
            if any(k[5:]):
                pat_total_data_list.append(k[1:])
        elif k[0] == 'Category':
            if any(k[5:]):
                category_total_data_list.append(k[1:])

    table_create_params = []
    if len(variations_total_data_list):
        variations_all =  make_exact_all_list(variations_total_data_list)
        table_create_params.append(variations_all)
    if any(tpk_total_data[4:]) and tpk_total_data[2]:
        tpk_all = make_tpk_all(tpk_total_data)
        table_create_params.append(tpk_all)
    if any(broad_total_data[4:]):
        broad_all = make_broad_all(broad_total_data, keyword_negatives, phrases_negatives)
        table_create_params.append(broad_all)

    auto_close_neg_all = make_auto_neg_all(auto_close_neg_total_data, keyword_negatives, phrases_negatives)
    auto_close_all = make_auto_all(auto_close_total_data)

    auto_loose_neg_all = make_auto_neg_all(auto_loose_neg_total_data, keyword_negatives, phrases_negatives)
    auto_loose_all = make_auto_all(auto_loose_total_data)

    auto_subs_neg_all = make_auto_neg_all(auto_subs_neg_total_data, keyword_negatives, phrases_negatives)
    auto_subs_all = make_auto_all(auto_subs_total_data)

    auto_compl_neg_all = make_auto_neg_all(auto_compl_neg_total_data, keyword_negatives, phrases_negatives)
    auto_compl_all = make_auto_all(auto_compl_total_data)

    for _all in [auto_compl_all, auto_compl_neg_all, auto_subs_all, auto_subs_neg_all, auto_loose_all,
                 auto_loose_neg_all, auto_close_all, auto_close_neg_all]:
        table_create_params.append(_all)
    if len(exact_total_data_list):
        exact_all = make_exact_all_list(exact_total_data_list)
        table_create_params.append(exact_all)
    if len(brands_total_data_list):
        brands_all = make_exact_all_list(brands_total_data_list)
        table_create_params.append(brands_all)
    if len(pat_total_data_list):
        # for pat_stage in sort_pats(pat_total_data_list):
        #     pat_words, pat_all = make_pat_all_list(pat_stage)
        pat_all = make_pat_all_list(pat_total_data_list)[1]
        table_create_params.append(pat_all)
    if len(category_total_data_list):
        try:
            pat_words, pat_all = make_pat_all_list(pat_total_data_list)
        except ValueError:
            pat_words = []
        category_all = make_category_all_list(category_total_data_list, pat_words)
        table_create_params.append(category_all)

    table_name = f'{range_name.replace("clusters", "bulk")}'
    worksheets_list = [worksheet.title for worksheet in sht1.worksheets()]

    if f'{range_name.replace("clusters", "bulk")}' not in worksheets_list:
        sht1.add_worksheet(title=table_name, rows=100, cols=20)
    output_file_name = f'{range_name.replace("clusters", "bulk")}.xlsx'
    pd.concat(table_create_params).reset_index().drop('index', axis=1).to_excel(f'{MEDIA_ROOT}{output_file_name}', index=False)
    read_file = pd.read_excel(f'{MEDIA_ROOT}{output_file_name}')
    read_file.to_csv(f'{MEDIA_ROOT}{table_name}.csv', index=False, header=True)
    sht1.values_update(
        table_name,
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': list(csv.reader(open(f'media/{table_name}.csv')))}
    )
    return output_file_name
