import pandas as pd
import httplib2
import gspread
from googleapiclient import discovery
from collections import defaultdict

from clusters.remove_duplicates import remove_duplicates

API_KEY = 'AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY'


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
    spreadsheet_id = get_table_id(table_link)

    gc = gspread.service_account(filename='clusters/apikey.json')
    table = gc.open_by_key(spreadsheet_id)
    range_name = table.sheet1.title
    remove_duplicates(spreadsheet_id, range_name)
    df_total = get_data_frame(API_KEY, spreadsheet_id, range_name)
    phrase = range_name
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
            category.append([k[0]] + [get_first_number(x) for x in k[1:] if x is not None and x != ''])
        elif len(k[0]) != 0:
            oth = [[q.strip() for q in x.split(',')] for x in k[1:] if x is not None and x != '']
            oth_new = []
            for t in oth:
                qq = [x for x in t if x != '']
                other.append(tuple([k[0], tuple(qq)]))

    keywords_filtered = list((set(keywords) - set(tpk)) - set(str_top))
    keywords_filtered = list((set(keywords_filtered) - set(str_low)) - set(broad))
    keywords_tuples = [tuple(x.split(' ')) for x in keywords_filtered]

    keywords_total_dict = dict()

    for p in keywords_tuples:
        for r in other:
            if p in keywords_total_dict.keys():
                continue
            if len(set(p).intersection(set(r[1]))) > 0:
                keywords_total_dict[p] = r

    rest = []
    for p in keywords_tuples:
        if p not in keywords_total_dict.keys():
            rest.append(' '.join(p))

    total_result = defaultdict(list)
    for k, v in keywords_total_dict.items():
        total_result[v].append(' '.join(k))

    list_total = []

    list_total.append(['TPK', phrase + ' (TPK)', 'tpk', values["tpk"]["scu"], values['tpk']['bid']] + tpk)
    list_total.append([None])
    list_total.append([None])

    list_total.append(['Exact', phrase + ' (STR Top)', 'STR Top', values['str_top']['scu'],
                       values['str_top']['bid']] + str_top)
    list_total.append([None])
    list_total.append([None])

    list_total.append(['Exact', phrase + ' (STR Low)', 'STR Low', values['str_low']['scu'],
                       values['str_low']['bid']] + str_low)
    list_total.append([None])
    list_total.append([None])

    for q in other:
        if q in total_result:
            if 'exact top' in q[0].lower():
                list_total.append(['Exact', phrase + ' (' + q[0] + ')', q[1][0], values['exact_top']['scu'],
                                   values['exact_top']['bid']] + total_result[q])
                list_total.append([None])
                list_total.append([None])

    for q in other:
        if q in total_result:
            if 'exact' in q[0].lower() and 'low' not in q[0].lower() and 'top' not in q[0].lower():
                list_total.append(['Exact', phrase + ' (' + q[0] + ')', q[1][0], values['exact']['scu'],
                                   values['exact']['bid']] + total_result[q])
                list_total.append([None])
                list_total.append([None])

    for q in other:
        if q in total_result:
            if 'exact low' in q[0].lower():
                list_total.append(['Exact', phrase + ' (' + q[0] + ')', q[1][0], values['exact_low']['scu'],
                                   values['exact_low']['bid']] + total_result[q])
                list_total.append([None])
                list_total.append([None])

    list_total.append(['Broad', phrase + ' (Broad)', 'broad', values['broad']['scu'], values['broad']['bid']] + broad)
    list_total.append([None])
    list_total.append([None])

    for q in other:
        if q in total_result:
            if 'brands' in q[0].lower():
                list_total.append([q[0], phrase + ' (' + q[0] + ')', q[1][0], values['brands']['scu'],
                                   values['brands']['bid']] + total_result[q])
                list_total.append([None])
                list_total.append([None])

    for q in other:
        if q in total_result:
            if 'variation' in q[0].lower():
                list_total.append([q[0], phrase + ' (' + q[0] + ')', q[1][0], values['variation']['scu'],
                                   values['variation']['bid']] + total_result[q])
                list_total.append([None])
                list_total.append([None])
    maxi = 0
    for p in list_total:
        maxi = max(maxi, len(p))

    pat_negatives = []

    for p in tpas:
        pat_negatives.extend(p[1:])
        maxi = max(maxi, len(p) + 4)
        list_total.append(['PAT', phrase + ' (PAT)', p[0], values[p[0].lower()]['scu'], values[p[0].lower()]['bid']] + p[1:])
        list_total.append([None])
        list_total.append([None])

    for p in category:
        maxi = max(maxi, len(p) + 4)
        list_total.append(['Category', phrase + ' (category)', p[0].lower(), values['category']['scu'],
                           values['category']['bid']] + p[1:])
        list_total.append([None])
        list_total.append([None])

    for type_ in ['Close', 'Loose', 'Subs', 'Compl']:
        list_total.append(['Auto', phrase + f' (Auto Negatives {type_})', 'auto', values['auto_negatives']['scu'],
                           values['auto_negatives']['bid']])
        list_total.append([None])
        list_total.append([None])

    for type_ in ['Close', 'Loose', 'Subs', 'Compl']:
        list_total.append(['Auto', phrase + f' (Auto {type_})', 'auto', values['auto']['scu'],
                           values['auto']['bid']])
        list_total.append([None])
        list_total.append([None])

    list_total.append(['NegativePhrases', '', '', '', ''] + negative)
    list_total.append([None])
    list_total.append([None])

    list_total.append(['NegativeExacts', '', '', '', ''] + keywords + tpk + str_low + str_top)
    list_total.append([None])
    list_total.append([None])

    list_total.append(['NegativePATs', '', '', '', ''] + pat_negatives)
    list_total.append([None])
    list_total.append([None])

    # for q in list_total:
    #     q.extend([None] * (maxi - len(q)))

    worksheet_objs = table.worksheets()
    worksheets_list = []
    for worksheet in worksheet_objs:
        worksheets_list.append(worksheet.title)

    if range_name + ' (clusters)' not in worksheets_list:
        table.add_worksheet(title=range_name + ' (clusters)', rows="100", cols="20")

    clusters = table.worksheet(range_name + ' (clusters)')

    clusters.update('C1', pd.DataFrame(list_total).T.values.tolist())