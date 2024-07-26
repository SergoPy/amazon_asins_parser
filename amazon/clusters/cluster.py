import pandas as pd
import httplib2
import gspread
from googleapiclient import discovery
from collections import defaultdict

from clusters.remove_duplicates import remove_duplicates

API_KEY = 'AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY'
list_total = []


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


def split_and_append(list_name, phrase, keyword, values_dict, category_list, count, prefix=None):
    iteration = 1
    print(f"keyword: {keyword}, len(category_list): {len(category_list)}")
    for i in range(0, len(category_list), count):
        print(f"count: {count}")
        current_block = category_list[i:i+count]
        iteration_suffix = f" - {iteration}" if iteration > 1 else ""
        new_phrase = phrase + \
            (f" ({prefix})" if prefix else "") + \
            f" | {keyword} " + iteration_suffix
        list_total.append([list_name, new_phrase, keyword,
                          values_dict['scu'], values_dict['bid']] + current_block)
        list_total.append([None])
        list_total.append([None])
        iteration += 1
    if len(category_list) == 0:
        print(f"len(category_list) - IF: {len(category_list)}")
        iteration_suffix = f" {iteration}" if iteration > 1 else ""
        new_phrase = phrase + \
            (f" ({prefix})" if prefix else "") + iteration_suffix
        list_total.append([list_name, new_phrase, keyword,
                          values_dict['scu'], values_dict['bid']] + category_list)
        list_total.append([None])
        list_total.append([None])


def get_first_number(x):
    res = x.split('/')
    for x in res:
        try:
            int(x)
            return x
        except ValueError:
            pass
    return 0


def get_table_id(table_link):
    return table_link.split('/d/')[1].split('/')[0]


def google_sheets_clusters(table_link, values):

    print(f"company_values: {values}")
    spreadsheet_id = get_table_id(table_link)
    gc = gspread.service_account(filename='clusters/apikey.json')
    table = gc.open_by_key(spreadsheet_id)
    range_name = table.sheet1.title
    remove_duplicates(spreadsheet_id, range_name)
    df_total = get_data_frame(API_KEY, spreadsheet_id, range_name)
    phrase = range_name
    campaign_count = int(values['mkpc_key'])
    keywords = []
    tpk = []
    str_top = []
    str_low = []
    broad = []
    negative = []
    tpas = list()
    category = list()
    other = list()
    variations = []

    for k in df_total.T.values:
        if k[0].lower() == 'keywords':
            keywords = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'tpk':
            tpk = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'str top':
            str_top = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'str low':
            str_low = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'broad':
            broad = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'variation':
            variations = [x for x in k[1:] if x is not None and x != '']
        elif 'negative' in k[0].lower() and 'phrase' in k[0].lower():
            negative = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() in ['tpa', 'tca', 'ca', 'ra', 'lsa', 'lpa']:
            tpas.append([x for x in k if x is not None and x != ''])
        elif k[0].lower() in ['category']:
            category.append([k[0]] + [get_first_number(x)
                            for x in k[1:] if x is not None and x != ''])
        elif len(k[0]) != 0:
            oth = [[q.strip() for q in x.split(',')]
                   for x in k[1:] if x is not None and x != '']
            oth_new = []
            for t in oth:
                qq = [x for x in t if x != '']
                print(f"k[0]: {k[0]}, qq: {qq}")
                other.append(tuple([k[0], tuple(qq)]))

    keywords_filtered = list((set(keywords) - set(tpk)) - set(str_top))
    keywords_filtered = list(
        (set(keywords_filtered) - set(str_low)) - set(broad))
    keywords_tuples = [tuple(x.split(' ')) for x in keywords_filtered]

    keywords_total_dict = dict()

    for p in keywords_tuples:
        for r in other:
            if p in keywords_total_dict.keys():
                continue
            if len(set(p).intersection(set(r[1]))) > 0:
                keywords_total_dict[p] = r
    print(f"keywords_total_dict: {keywords_total_dict}")

    rest = []
    for p in keywords_tuples:
        if p not in keywords_total_dict.keys():
            rest.append(' '.join(p))

    total_result = defaultdict(list)
    for k, v in keywords_total_dict.items():
        total_result[v].append(' '.join(k))
    print(f"total_result: {total_result}")

    # TPK, Exact STR Top, Exact STR Low, Variation
    split_and_append('TPK', phrase, 'tpk',
                     values["tpk"], tpk, campaign_count, "TPK")
    split_and_append('Exact', phrase, 'STR Top',
                     values['str_top'], str_top, campaign_count, "STR Top")
    split_and_append('Exact', phrase, 'STR Low',
                     values['str_low'], str_low, campaign_count, "STR Low")
    split_and_append('Variation', phrase, 'variation',
                     values['variation'], variations, campaign_count, "variation")

    # Other categories
    for q in other:
        if q in total_result:
            if 'exact top' in q[0].lower():
                split_and_append(
                    'Exact', phrase, q[1][0], values['exact_top'], total_result[q], campaign_count, q[0])

    for q in other:
        if q in total_result:
            if 'exact' in q[0].lower() and 'low' not in q[0].lower() and 'top' not in q[0].lower():
                split_and_append(
                    'Exact', phrase, q[1][0], values['exact'], total_result[q], campaign_count, q[0])

    for q in other:
        if q in total_result:
            if 'exact low' in q[0].lower():
                split_and_append(
                    'Exact', phrase, q[1][0], values['exact_low'], total_result[q], campaign_count, q[0])

    split_and_append('Broad', phrase, 'broad',
                     values['broad'], broad, campaign_count)

    for q in other:
        if q in total_result:
            if 'brands' in q[0].lower():
                split_and_append(
                    q[0], phrase, q[1][0], values['brands'], total_result[q], campaign_count)

    for q in other:
        if q in total_result:
            if 'variation' in q[0].lower():
                split_and_append(
                    q[0], phrase, q[1][0], values['variation'], total_result[q], campaign_count)

    # PAT Negatives
    pat_negatives = []
    for p in tpas:
        pat_negatives.extend(p[1:])
        split_and_append(
            'PAT', phrase, p[0], values[p[0].lower()], p[1:], campaign_count, 'PAT')

    # Category
    for p in category:
        split_and_append('Category', phrase, p[0].lower(
        ), values['category'], p[1:], campaign_count, 'category')

    # Auto Negatives
    for type_ in ['Close', 'Loose', 'Subs', 'Compl']:
        split_and_append('Auto', phrase, 'auto', values['auto_negatives'], [
        ], campaign_count, f'Auto Negatives {type_}')

    # Auto
    for type_ in ['Close', 'Loose', 'Subs', 'Compl']:
        split_and_append('Auto', phrase, 'auto', values['auto'], [
        ], campaign_count, f'Auto {type_}')

    # NegativePhrases
    split_and_append('NegativePhrases', '', '', {
                     'scu': '', 'bid': ''}, negative, campaign_count)

    # NegativeExacts
    negative_exacts = keywords + tpk + str_low + str_top
    split_and_append('NegativeExacts', '', '', {
                     'scu': '', 'bid': ''}, negative_exacts, campaign_count)

    # NegativePATs
    split_and_append('NegativePATs', '', '', {
                     'scu': '', 'bid': ''}, pat_negatives, campaign_count)

    worksheet_objs = table.worksheets()
    worksheets_list = []
    for worksheet in worksheet_objs:
        worksheets_list.append(worksheet.title)

    if range_name + ' (clusters)' not in worksheets_list:
        table.add_worksheet(title=range_name +
                            ' (clusters)', rows="100", cols="20")

    clusters = table.worksheet(range_name + ' (clusters)')

    clusters.update('C1', pd.DataFrame(list_total).T.values.tolist())
