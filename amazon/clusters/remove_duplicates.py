
import httplib2
import inflect
import pandas as pd
import gspread

from apiclient import discovery

from clusters.utils import indexes_to_a1, normalize_text

API_KEY = 'AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY'
SPREADSHEET_RULE_ID = '10IrWEmWfshmP74K2SYKi0QZbiWhEFgCW9m0TNzePetM'


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


def get_rule_df(rule_name):
    return get_data_frame(API_KEY, SPREADSHEET_RULE_ID, rule_name)


def update_column(worksheet, column_name, data):
    coords = worksheet.find(column_name)
    row, col = coords.row + 1, coords.col
    values_list = [[elem] for elem in data]
    len_column = len(worksheet.col_values(col))
    while len(values_list) != len_column:
        values_list.append([''])
    worksheet.update(
        f'{indexes_to_a1(row, col)}:{indexes_to_a1(row + len_column, col)}', values_list)


def remove_duplicates(spreadsheet_id, range_name):
    data = get_data_frame(API_KEY, spreadsheet_id, range_name)
    inflect_engine = inflect.engine()
    keywords = []

    for k in data.T.values:
        if k[0].lower() == 'seed':
            k = [k[0]] + [normalize_text(keyword)
                          for keyword in k[1:] if keyword]
            keywords.extend([tuple(['seed:'] + x.split(' '))
                            for x in k[1:] if x is not None and x != ''])

    for k in data.T.values:
        if 'str' in k[0].lower():
            k = [k[0]] + [normalize_text(keyword)
                          for keyword in k[1:] if keyword]
            keywords.extend([tuple([k[0].lower() + ':'] + x.split(' '))
                            for x in k[1:] if x is not None and x != ''])

    for k in data.T.values:
        if k[0].lower() == 'keywords':
            k = [k[0]] + [normalize_text(keyword)
                          for keyword in k[1:] if keyword]
            keywords.extend([tuple(['keyword:'] + x.split(' '))
                            for x in k[1:] if x is not None and x != ''])

    prep_df = get_rule_df('Prepositions')
    preps = list(prep_df[0])

    keywords_ignore_preps = []

    for k in keywords:
        res = []                 
        for t in k:
            if t in preps:
                continue
            res.append(t)
        keywords_ignore_preps.append(tuple(res))

    reg_verbs_dict = dict()

    verbs_df = get_rule_df('Regular Verbs')

    for k in verbs_df.values:
        reg_verbs_dict[k[1].lower()] = k[0].lower()

    keywords_regular_verbs = []

    for k in keywords_ignore_preps:
        res = []
        for t in k:
            if t in reg_verbs_dict.keys():
                res.append(reg_verbs_dict[t])
            else:
                res.append(t)

        keywords_regular_verbs.append(res)

    plural_nouns_dict = dict()
    plural_nouns_df = get_rule_df('Plural Nouns')

    for k in plural_nouns_df.values:
        plural_nouns_dict[k[1].lower()] = k[0].lower()

    keywords_no_plurals = []

    for k in keywords_regular_verbs:
        res = []
        for t in k:
            try:
                if t in plural_nouns_dict.keys():
                    res.append(plural_nouns_dict[t])
                elif t[-3:] in ['ses', 'xes', 'hes']:
                    res.append(t[:-2])
                elif t[-1] == 's' and t[-2:] != 'ss':
                    res.append(t[:-1])
                else:
                    res.append(t)
            except IndexError:
                res.append(t)

        keywords_no_plurals.append(res)

    ing_dict = dict()
    ing_df = get_rule_df('Ing')

    for k in ing_df.values:
        ing_dict[k[1].lower()] = k[0].lower()
        ing_dict[k[2].lower()] = k[0].lower()

    keywords_no_ing = []

    for k in keywords_no_plurals:
        res = []
        for t in k:
            res.append(t)

        keywords_no_ing.append(res)

    other_dict = dict()
    other_df = get_rule_df('Other')

    for k in other_df.values:
        other_dict[k[1].lower()] = k[0].lower()

    keywords_total = []

    for k in keywords_no_ing:
        res = []
        for t in k:
            res.append(t)

        keywords_total.append(tuple(res[1:]))


    qq = pd.DataFrame([[(' '.join(k), i) for i, k in enumerate(keywords)], [
                      ' '.join(kw) for kw in keywords_total]]).T
    qq.columns = ['initial', 'normalized']

    qq_grouped = qq.groupby('normalized')['initial'].apply(list).reset_index()
    qq_grouped['initial'] = qq_grouped.initial.apply(lambda x: x[0])
    qq_grouped['normalized'] = qq_grouped.normalized.apply(lambda x: x)

    qq_grouped['index'] = qq_grouped['initial'].apply(lambda x: x[1])
    qq_grouped['keyword'] = qq_grouped['normalized'].apply(
        lambda x: x)
    qq_grouped['category'] = qq_grouped['initial'].apply(
        lambda x: x[0].split(': ')[0])

    total_res = qq_grouped.sort_values('index')[['category', 'keyword']]

    keywords = list(total_res[total_res.category == 'keyword'].keyword)
    seed = list(total_res[total_res.category == 'seed'].keyword)
    str_top = list(total_res[total_res.category == 'str top'].keyword)
    str_low = list(total_res[total_res.category == 'str low'].keyword)

    gc = gspread.service_account(filename='clusters/apikey.json')
    sht1 = gc.open_by_key(spreadsheet_id)
    worksheet = sht1.worksheet(range_name)

    print(f"keywords: {keywords}")
    print(f"seed: {seed}")
    print(f"str_low: {str_low}")
    print(f"str_top: {str_top}")
    if len(keywords) > 1:
        update_column(worksheet, 'KEYWORDS', keywords)
    if len(seed) > 1:
        update_column(worksheet, 'SEED', seed)
    if len(str_low) > 1:
        update_column(worksheet, 'STR Low', str_low)
    if len(str_top) > 1:
        update_column(worksheet, 'STR Top', str_top)
