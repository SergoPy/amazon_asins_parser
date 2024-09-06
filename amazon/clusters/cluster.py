from difflib import SequenceMatcher
import inflect
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from amazon.google_api import GoogleSheetsApi
from amazon.utils import indexes_to_a1
from clusters.remove_duplicates import remove_duplicates
from webscraper.models import Campaign
import re
import pandas as pd
import httplib2
import gspread
from googleapiclient import discovery
from collections import defaultdict
from django.conf import settings
import nltk
nltk.download('wordnet')


def singularize(word):
    lemmatizer = WordNetLemmatizer()
    lemma = lemmatizer.lemmatize(word)
    return lemma if lemma != word else lemmatizer.lemmatize(word, 'v')


def is_similar(word1, word2, threshold=0.82):
    return SequenceMatcher(None, word1, word2).ratio() > threshold


def process_phrases(broad):
    processed_phrases = set()
    normalized_phrases = set()
    p = inflect.engine()

    for phrase in broad:
        words = phrase.split()
        singular_words = []
        for word in words:
            word = p.singular_noun(word) or word
            if word.isdigit() or len(word) <= 3:
                singular_words.append(word)
            else:
                singular_words.append(singularize(word))

        phrase_with_plus = "+" + " +".join(singular_words)
        normalized_phrase = " ".join(singular_words)

        # Перевірка на схожість з існуючими фразами
        if not any(is_similar(normalized_phrase, existing) for existing in normalized_phrases):
            processed_phrases.add(phrase_with_plus)
            normalized_phrases.add(normalized_phrase)

    return list(processed_phrases)


def prepare_to_sheet(single_list):
    plural_list = []
    for single in single_list:
        plural_list.append([f"'{single}"])

    return plural_list


def update_words_col(table_link, write_data):
    apikey_file_path = settings.APIKEY_FILEPATH
    table_id = get_table_id(table_link)
    googlesheets_api = GoogleSheetsApi(
        table_id, apikey_file_path)
    row, col = googlesheets_api.get_cord_by_name('Words')
    num_of_record = len(write_data)

    diapason = f'{indexes_to_a1(row, col)}:' \
        f'{indexes_to_a1(row + num_of_record, col)}'

    # print(f"diapason: {diapason}")
    googlesheets_api.update(
        diapason, write_data)


def separate_words(phrases):
    pass


API_KEY = 'AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY'
list_total = list()
campaign_names = list()


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
    campaign_name = phrase + \
        (f" ({prefix})" if prefix else "") + f" | {keyword} "
    campaign_names.append(campaign_name)

    for i in range(0, len(category_list), count):
        current_block = category_list[i:i+count]
        iteration_suffix = f" {iteration}" if iteration > 1 else ""
        new_phrase = phrase + \
            (f" ({prefix})" if prefix else "") + \
            f" | {keyword} " + iteration_suffix
        list_total.append([list_name, new_phrase, keyword,
                          values_dict['scu'], values_dict['bid']] + current_block)
        list_total.append([' ', ' ', 'Custom Bid'])
        list_total.append([' ', ' ', 'Piacement ToS'])
        iteration += 1

    if len(category_list) == 0:
        iteration_suffix = f" {iteration}" if iteration > 1 else ""
        new_phrase = phrase + \
            (f" ({prefix})" if prefix else "") + \
            f" | {keyword} " + iteration_suffix
        list_total.append([list_name, new_phrase, keyword,
                          values_dict['scu'], values_dict['bid']] + category_list)
        list_total.append(['', '', 'Custom Bid'])
        list_total.append(['', '', 'Piacement ToS'])


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
    # print(f"values: {values}")
    spreadsheet_id = get_table_id(table_link)
    gc = gspread.service_account(filename='clusters/apikey.json')
    table = gc.open_by_key(spreadsheet_id)
    range_name = table.sheet1.title
    print(f"table: {table}")
    print(f"range_name: {range_name}")
    remove_duplicates(spreadsheet_id, range_name)
    df_total = get_data_frame(API_KEY, spreadsheet_id, range_name)
    phrase = range_name
    campaign_count = max(25, int(values['mkpc_key']))

    keywords = []
    seed = []
    words = []
    str_top = []
    str_low = []
    broad = []
    negative = []
    brand_def = []
    adv_asin = []
    tpas = list()
    category = list()
    other = list()
    variations = []

    for k in df_total.T.values:
        # print(f"k: {k}")
        if k[0].lower() == 'str top':
            str_top = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() == 'seed':
            seed = [x for x in k[1:] if x is not None and x !=
                    '' and x not in str_top]
        elif k[0].lower() == 'keywords':
            keywords = [x for x in k[1:]
                        if x is not None and x != '' and x not in str_top]
        elif k[0].lower() == 'str low':
            str_low = [x for x in k[1:] if x is not None and x !=
                       '' and x not in str_top]
        elif k[0].lower() == 'brand defense':
            brand_def = [x for x in k[1:] if x is not None and x !=
                         '' and x not in str_top]
        elif k[0].lower() == 'advertised asin':
            adv_asin = [x for x in k[1:] if x is not None and x !=
                        '' and x not in str_top]
        elif k[0].lower() == 'broad':
            broad = [x for x in k[1:] if x is not None and x !=
                     '' and x not in str_top]
        elif k[0].lower() == 'Words':
            words = [x for x in k[1:] if x is not None and x !=
                     '' and x not in str_top]
        elif k[0].lower() == 'variation':
            variations = [x for x in k[1:]
                          if x is not None and x != '' and x not in str_top]
        elif 'negative' in k[0].lower() and 'phrase' in k[0].lower():
            negative = [x for x in k[1:] if x is not None and x != '']
        elif k[0].lower() in ['tpa', 'tca', 'ca', 'ra', 'lsa', 'lpa']:
            no_length_check_keys = ['tpa', 'tca', 'ca', 'ra', 'lsa', 'lpa']
            tpas.append([x for x in k
                         if x is not None and
                         x != '' and
                         (x.lower() in no_length_check_keys or len(x) == 10) and
                         x not in str_top])
        elif k[0].lower() in ['category']:
            category.append([k[0]] + [get_first_number(x)
                            for x in k[1:] if x is not None and x != '' and x not in str_top])
        elif len(k[0]) != 0:
            oth = [[q.strip() for q in x.split(',')]
                   for x in k[1:] if x is not None and x != '' and x not in str_top]
            oth_new = []
            for t in oth:
                qq = [x for x in t if x != '']
                other.append(tuple([k[0], tuple(qq)]))

    broad.extend(seed)

    new_pharases = set()
    for phrase in broad:
        new_pharases.update(phrase.split())

    words = process_phrases(new_pharases)

    separated_words = prepare_to_sheet(words)

    update_words_col(table_link, separated_words)

    broad = process_phrases(broad)

    keywords_filtered = list((set(keywords) - set(seed)))
    keywords_filtered = list(
        (set(keywords_filtered) - set(str_low)) - set(broad))
    keywords_tuples = [
        tuple(x.split(' '))
        for x in keywords_filtered
        if len(x) <= 50
    ]

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

    # SEED, Exact STR Top, Exact STR Low, Variation
    split_and_append('SEED', phrase, 'seed',
                     values["seed"], seed, 10000, "SEED")
    split_and_append('Exact', phrase, 'STR Top',
                     values['str_top'], str_top, campaign_count, "STR Top")
    split_and_append('Exact', phrase, 'STR Low',
                     values['str_low'], str_low, campaign_count, "STR Low")
    split_and_append('Variation', phrase, 'variation',
                     values['variation'], variations, campaign_count, "variation")
    split_and_append('Broad', phrase, 'broad',
                     values['broad'], broad, 10000, "Broad")
    split_and_append('Words', phrase, 'words',
                     values['words'], words, 10000, "Words")
    split_and_append('Brand Defense', phrase, 'brand defense',
                     values["brand_def"], brand_def, 10000, "Brand Defense")
    split_and_append('Advertised ASIN', phrase, 'advertised asin',
                     values["adv_asin"], adv_asin, 10000, "Advertised ASIN")

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

    split_and_append(
        'Exact Other', phrase, 'Exact Other', {"bid": " ", "scu": " "}, rest, campaign_count, 'Exact Other')

    for q in other:
        # print(f"q from other: {q}, q[0]:{q[0]}  q[1][0]: {q[1][0]}, values['brands']: {values['brands']}, total_result[q]: {total_result[q]}")
        if q in total_result:
            if 'brands' in q[0].lower():
                split_and_append(
                    q[0], phrase, q[1][0], values['brands'], total_result[q], campaign_count, q[0])

    for q in other:
        if q in total_result:
            if 'variation' in q[0].lower():
                split_and_append(
                    q[0], phrase, q[1][0], values['variation'], total_result[q], campaign_count, q[0])

    # PAT Negatives
    pat_negatives = []
    # print(f"tpas: {tpas}")
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
    split_and_append('NegativePhrases', phrase, 'NegativePhrases', {
                     'scu': '', 'bid': ''}, negative, campaign_count, "NegativePhrases")

    # NegativeExacts
    negative_exacts = keywords + seed + str_low + str_top
    split_and_append('NegativeExacts', phrase, 'NegativeExacts', {
                     'scu': '', 'bid': ''}, negative_exacts, campaign_count, "NegativeExacts")

    # NegativePATs
    split_and_append('NegativePATs', phrase, 'NegativePATs', {
                     'scu': '', 'bid': ''}, pat_negatives, campaign_count, "NegativePATs")

    worksheet_objs = table.worksheets()
    worksheets_list = []
    for worksheet in worksheet_objs:
        worksheets_list.append(worksheet.title)

    if range_name + ' (clusters)' not in worksheets_list:
        table.add_worksheet(title=range_name +
                            ' (clusters)', rows="100", cols="20")

    clusters = table.worksheet(range_name + ' (clusters)')

    clusters.update('C1', pd.DataFrame(list_total).T.values.tolist())

    upload_campaign_to_db()


def extract_text(input_string):

    match = re.search(r'\(([^)]+)\)', input_string)
    if match:
        return match.group(1) + input_string.split(')')[1]
    return None


def upload_campaign_to_db():
    campaigns = list()
    unique_campaign_names = set(campaign_names)
    Campaign.objects.all().delete()
    for campaign_name in unique_campaign_names:
        filter_campaign_name = extract_text(campaign_name)
        campaigns.append(Campaign(name=filter_campaign_name))
    # print(f"campaigns from upload_campaign_to_db: {campaigns}")
    Campaign.objects.bulk_create(campaigns)
