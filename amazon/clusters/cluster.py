from difflib import SequenceMatcher
import time
import inflect
from nltk.stem import WordNetLemmatizer
from amazon.google_api import GoogleSheetsApi
from amazon.utils import indexes_to_a1
from clusters.remove_duplicates import remove_duplicates, remove_duplicates_from_list
from webscraper.models import Campaign
import re
import pandas as pd
import httplib2
import gspread
from googleapiclient import discovery
from collections import defaultdict
from django.conf import settings
import nltk

nltk.download("wordnet")


def singularize(word):
    lemmatizer = WordNetLemmatizer()
    lemma = lemmatizer.lemmatize(word)
    return lemma if lemma != word else lemmatizer.lemmatize(word, "v")


def is_similar(word1, word2, threshold=0.82):
    return SequenceMatcher(None, word1, word2).ratio() > threshold


def process_phrases(broad):
    processed_phrases = set()
    p = inflect.engine()

    for phrase in broad:
        words = phrase.split()
        singular_words = []
        for word in words:
            clean_word = word.lstrip("+") 
            clean_word = p.singular_noun(clean_word) or clean_word
            if clean_word.isdigit() or len(clean_word) <= 3:
                singular_words.append(clean_word)
            else:
                singular_words.append(singularize(clean_word))

        phrase_with_plus = "+" + " +".join(singular_words)
        processed_phrases.add(phrase_with_plus)

        # normalized_phrase = " ".join(singular_words)

        # # Перевірка на схожість з існуючими фразами
        # if not any(is_similar(normalized_phrase, existing) for existing in normalized_phrases):
        #     normalized_phrases.add(normalized_phrase)

    return list(processed_phrases)


def process_words(broad):
    processed_phrases = set()
    normalized_phrases = set()
    stop_words = {
        "a",
        "about",
        "above",
        "across",
        "after",
        "against",
        "along",
        "among",
        "around",
        "at",
        "before",
        "behind",
        "below",
        "beside",
        "between",
        "by",
        "during",
        "for",
        "from",
        "in",
        "inside",
        "into",
        "near",
        "of",
        "on",
        "over",
        "past",
        "since",
        "through",
        "to",
        "under",
        "until",
        "up",
        "with",
        "without",
    }
    p = inflect.engine()

    for phrase in broad:
        words = phrase.split()
        singular_words = []
        for word in words:
            word = p.singular_noun(word) or word
            if word.isdigit() or len(word) <= 3 or word.lower() in stop_words:
                singular_words.append(word)
            else:
                singular_words.append(singularize(word))

        phrase_with_plus = "+" + " +".join(singular_words)
        normalized_phrase = " ".join(singular_words)

        # # Перевірка на схожість з існуючими фразами
        if not any(
            is_similar(normalized_phrase, existing) for existing in normalized_phrases
        ):
            processed_phrases.add(phrase_with_plus)
            normalized_phrases.add(normalized_phrase)

    return list(processed_phrases)


def prepare_to_sheet(single_list):
    plural_list = []
    for single in single_list:
        plural_list.append([f"'{single}"])

    return plural_list


def update_words_col(table_link, write_data, index_start=""):
    apikey_file_path = settings.APIKEY_FILEPATH
    table_id = get_table_id(table_link)
    googlesheets_api = GoogleSheetsApi(table_id, apikey_file_path)
    row, col = googlesheets_api.get_cord_by_name("Words")
    if index_start != "":
        write_data = ", ".join(item[0] for item in write_data)
        diapason = (
            f"{indexes_to_a1(index_start+2, col)}:"
            f"{indexes_to_a1(index_start+3, col)}"
        )
    else:
        num_of_record = len(write_data)

        diapason = (
            f"{indexes_to_a1(row, col)}:" f"{indexes_to_a1(row + num_of_record, col)}"
        )

    # print(f"diapason: {diapason}")
    googlesheets_api.update(diapason, write_data)



API_KEY = "AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY"
list_total = list()
campaign_names = list()


def get_data_frame(key, spreadsheet_id, range_name):
    discovery_url = "https://sheets.googleapis.com/$discovery/rest?" "version=v4"
    service = discovery.build(
        "sheets",
        "v4",
        http=httplib2.Http(),
        discoveryServiceUrl=discovery_url,
        developerKey=key,
    )

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    values = result.get("values", [])

    return pd.DataFrame(values)


def split_and_append(
    list_name, phrase, keyword, values_dict, category_list, count, prefix=None, pat_prefix=None
):
    iteration = 1
    tos_bid_cat_list = ["seed", "exact top"]
    campaign_name = (
        phrase
        + (f" ({prefix})" if prefix else "")
        + (f" - {keyword}" if keyword else "")
    )
    campaign_names.append(campaign_name)

    if keyword is not None and keyword != "":
        keyword = " - " + keyword

    for i in range(0, len(category_list), count):
        current_block = category_list[i : i + count]
        if pat_prefix:
            iteration_suffix = f" # {iteration}" if iteration > 1 else ""
        else:
            iteration_suffix = f" {iteration}" if iteration > 1 else ""

        new_phrase = (
            phrase
            + (f" | {prefix}" if prefix else "")
            + (f"{keyword}" if keyword else "")
            + iteration_suffix
        )
        list_total.append(
            [
                list_name,
                new_phrase,
                pat_prefix or prefix or list_name.lower(),
                values_dict["scu"],
                values_dict["bid"],
            ]
            + current_block
        )
        if prefix.lower() in tos_bid_cat_list or list_name.lower() in tos_bid_cat_list:
            list_total.append([" ", " ", " ", "Custom Bid"])
            list_total.append(
                [" ", " ", " ", "Adjustment ToS", values_dict.get("tos", "")]
            )
        else:
            list_total.extend([[], []])
        iteration += 1

    if len(category_list) == 0:
        iteration_suffix = f" {iteration}" if iteration > 1 else ""
        new_phrase = (
            phrase
            + (f" | {prefix} " if prefix else "")
            + (f"{keyword}" if keyword else "")
            + iteration_suffix
        )
        list_total.append(
            [
                list_name,
                new_phrase,
                pat_prefix or prefix or list_name.lower(),
                values_dict["scu"],
                values_dict["bid"],
            ]
            + category_list
        )
        if prefix.lower() in tos_bid_cat_list or list_name.lower() in tos_bid_cat_list:
            list_total.append([" ", " ", " ", "Custom Bid"])
            list_total.append(
                [" ", " ", " ", "Adjustment ToS", values_dict.get("tos", "")]
            )
        else:
            list_total.extend([[], []])


def get_first_number(x):
    res = x.split("/")
    for x in res:
        try:
            int(x)
            return x
        except ValueError:
            pass
    return 0


def get_table_id(table_link):
    return table_link.split("/d/")[1].split("/")[0]


# negative_exacts = keywords + seed + str_low + launched


def google_sheets_clusters(table_link, values, bulk_upload_status, request):
    global campaign_names
    global list_total
    # print(f"before  global campaign_names: {campaign_names}")
    campaign_names = []
    list_total = []
    # print(f"after  global campaign_names: {campaign_names}")

    spreadsheet_id = get_table_id(table_link)
    gc = gspread.service_account(filename="clusters/apikey.json")
    table = gc.open_by_key(spreadsheet_id)
    range_name = table.sheet1.title
    df_total = get_data_frame(API_KEY, spreadsheet_id, range_name)
    seed = []
    words = []
    brand_def = []
    adv_asin = []
    broad = []
    other = list()
    if bulk_upload_status:
        start_index = 0
        product_name = []
        sku = []
        bid = []
        tos = []
        launched = []
        for k in df_total.T.values:
            # print(f"k: {k}")
            if k[0].lower() == "launched":
                launched = [x for x in k[1:] if x is not None and x != ""]
            if k[0].lower() == "product name":
                product_names = [x for x in k[1:]]
            elif k[0].lower() == "self targeting":
                adv_asin = [x for x in k[1:]]
            elif k[0].lower() == "sku":
                sku = [x for x in k[1:]]
            elif k[0].lower() == "words":
                words = [x for x in k[1:] if x not in launched]
            elif k[0].lower() == "seed":
                seed = [x for x in k[1:] if x not in launched and len(x) <= 45]
            elif k[0].lower() == "bid":
                bid = [x for x in k[1:]]
            elif k[0].lower() == "tos adjustment":
                tos = [x for x in k[1:]]
            elif k[0].lower() == "brand defense":
                brand_def = [x for x in k[1:]]

        for start_index, product_name in enumerate(product_names):
            if product_name == None or product_name.lower() == "":
                continue
            else:
                time.sleep(5)
                finall_index = 0
                for finish_index, product in enumerate(
                    product_names[start_index + 1 :]
                ):
                    if product != None and product.lower() != "":
                        finall_index = finish_index + start_index
                        # print(
                        #     f" start_index: {start_index} finish_index: {finall_index};")
                        break
                if finall_index == 0:
                    finall_index = len(seed) - 1

                new_pharases = set()
                seed_for_clear = seed[start_index : finall_index + 1]

                clear_seed = remove_duplicates_from_list(seed_for_clear)

                for phrases in clear_seed:
                    new_pharases.update(phrases.split())

                specific_words = [
                    word
                    for word in words[start_index : finall_index + 1]
                    if word != "" and word is not None
                ]
                
                print(f"IS_STH_IN_WORDS:{specific_words}")
                print(f"words before if:{specific_words}")
                if len(specific_words) < 1:
                    specific_words = process_phrases(new_pharases)
                    print(f"words in if:{specific_words}")
                else:
                    specific_words = process_phrases(specific_words)
                    print(f"words in else:{specific_words}")

                broad = process_phrases(clear_seed)

                keywords_filtered = list((set(clear_seed)))
                keywords_tuples = [
                    tuple(x.split(" ")) for x in keywords_filtered if len(x) <= 45
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
                        rest.append(" ".join(p))

                total_result = defaultdict(list)
                for k, v in keywords_total_dict.items():
                    total_result[v].append(" ".join(k))

                parametrs = {
                    "scu": sku[start_index],
                    "bid": bid[start_index],
                    "tos": tos[start_index],
                }
                if len(clear_seed) >= 1:
                    split_and_append(
                        "SEED", product_name, "", parametrs, clear_seed, 10000, "SEED"
                    )
                parametrs = {"scu": sku[start_index], "bid": bid[start_index]}
                if len(brand_def[start_index:finall_index]) >= 1:
                    split_and_append(
                        "Brand Defense",
                        product_name,
                        "",
                        parametrs,
                        brand_def[start_index:finall_index],
                        10000,
                        "Brand Defense",
                    )
                if len(adv_asin[start_index:finall_index]) >= 1:
                    split_and_append(
                        "Self Targeting",
                        product_name,
                        "",
                        parametrs,
                        adv_asin[start_index:finall_index],
                        10000,
                        "Self",
                    )
                parametrs = {
                    "scu": sku[start_index],
                    "bid": float(bid[start_index]) * 0.66,
                }
                if len(broad) >= 1:
                    split_and_append(
                        "Broad", product_name, "", parametrs, broad, 10000, "Broad"
                    )
                parametrs = {
                    "scu": sku[start_index],
                    "bid": float(bid[start_index]) * 0.2,
                }
                if len(specific_words) >= 1:
                    split_and_append(
                        "Words", product_name, "", parametrs, specific_words, 10000, "Words"
                    )
                parametrs = {
                    "scu": sku[start_index],
                    "bid": float(bid[start_index]) * 0.55,
                }
                # Auto Negatives
                for type_ in ["Close", "Loose", "Subs", "Compl"]:
                    split_and_append(
                        "Auto",
                        product_name,
                        "",
                        parametrs,
                        [],
                        1000000,
                        f"Auto Negatives {type_}",
                    )
                parametrs = {
                    "scu": sku[start_index],
                    "bid": float(bid[start_index]) * 0.33,
                }
                # Auto
                for type_ in ["Close", "Loose", "Subs", "Compl"]:
                    split_and_append(
                        "Auto",
                        product_name,
                        "",
                        parametrs,
                        [],
                        1000000,
                        f"Auto {type_}",
                    )

    else:
        remove_duplicates(spreadsheet_id, range_name)
        df_total = get_data_frame(API_KEY, spreadsheet_id, range_name)
        phrase = range_name
        campaign_count = max(1, int(values["mkpc_key"]))

        keywords = []
        words = []
        launched = []
        str_low = []

        negative = []

        tpas = list()
        category = list()
        other = list()
        # variations = []
        tmp_arr = []

        for k in df_total.T.values:
            if k[0].lower() == "launched":
                launched = [x for x in k[1:] if x is not None and x != ""]
            elif k[0].lower() == "seed":
                seed = [
                    x
                    for x in k[1:]
                    if x is not None and x != "" and x not in launched and len(x) <= 45
                ]
            elif k[0].lower() == "keywords":
                keywords = [
                    x
                    for x in k[1:]
                    if x is not None and x != "" and x not in launched and len(x) <= 45
                ]
            elif k[0].lower() == "str low":
                str_low = [
                    x for x in k[1:] if x is not None and x != "" and x not in launched
                ]
            elif k[0].lower() == "brand defense":
                brand_def = [
                    x for x in k[1:] if x is not None and x != "" and x not in launched
                ]
            elif k[0].lower() == "self targeting":
                adv_asin = [
                    x for x in k[1:] if x is not None and x != "" and x not in launched
                ]
            elif k[0].lower() == "broad":
                broad = [
                    x
                    for x in k[1:]
                    if x is not None and x != "" and x not in launched and len(x) <= 45
                ]
            elif k[0].lower() == "words":
                words = [
                    x for x in k[1:] if x is not None and x != "" and x not in launched
                ]
            # elif k[0].lower() == "variation":
            #     variations = [
            #         x for x in k[1:] if x is not None and x != "" and x not in launched
            #     ]
            elif k[0].lower() == "category":
                category.append(
                    [k[0]]
                    + [
                        get_first_number(x)
                        for x in k[1:]
                        if x is not None and x != "" and x not in launched
                    ]
                )
            elif "negative" in k[0].lower() and "phrase" in k[0].lower():
                negative = [x for x in k[1:] if x is not None and x != ""]
            elif k[0] != "" and k[0].lower().split()[0] in [
                "tpa",
                "tca",
                "ca",
                "ra",
                "lsa",
                "lpa",
            ]: # тут ми проходимо по наших lpa[4...100], tca[200...23333]
                no_length_check_keys = ["tpa", "tca", "ca", "ra", "lsa", "lpa"]
                tmp_arr = [k[0].lower()]
                tmp_arr.extend(
                    [
                        x
                        for x in k[1:]
                        if x is not None
                        and x != ""
                        and (
                            x.lower().split()[0] in no_length_check_keys or len(x) == 10
                        )
                        and x not in launched
                    ]
                )
                tpas.append(tmp_arr)
            elif len(k[0]) != 0 and k[0].lower() not in [
                "photo",
                "title",
                "reviews",
                "rating",
                "price",
            ]: # тут ми відкидаємо все не потрібне(фото, відгуки, рейтинг і збираємо в oth ['exact low', 'exact', 'exact top', 'brands', "variation"])
                # if k[0].lower() in ['exact low', 'exact', 'exact top', 'brands', ]:
                oth = [
                    [q.strip().lower() for q in x.split(",")]
                    for x in k[1:]
                    if x is not None and x != "" and x not in launched
                ]
                for t in oth:
                    qq = [x for x in t if x != ""]
                    other.append(tuple([k[0], tuple(qq)])) # [('Brands', ('muse',)), ('Exact LOW', ('small',)), ('Exact', ('yard', 'garden')),...] тут ми зберігаємо ось в такому форматі
        
        
        if len(broad) < 1:
            broad.extend(seed)

        new_pharases = set()
        for phrases in seed:
            new_pharases.update(phrases.split())

        if len(words) < 1:
            words = process_phrases(new_pharases)
        else:
            words = process_phrases(words)
        broad = process_phrases(broad)

        keywords_filtered = list((set(keywords) - set(seed) - set(str_low)) - set(broad) - set(launched))

        keywords_tuples = [
            tuple(x.split(" ")) for x in keywords_filtered if len(x) <= 45
        ] #  [('gifts', 'for', 'women', 'over', '70'), ('hanging', 'outdoor', 'hummingbird', 'feeder'), ('decorative', 'hummingbird', 'feeders', 'for', 'outdoors'),...] - тут кейвордси розбиваємо на слова

        keywords_total_dict = dict()
        for p in keywords_tuples:
            for r in other:
                if p in keywords_total_dict.keys():
                    continue
                if len(set(p).intersection(set(r[1]))) > 0:
                    keywords_total_dict[p] = r # {('gifts', 'for', 'women', 'over', '70'): ('Exact', ('gift', 'gifts')), ('hanging', 'outdoor', 'hummingbird', 'feeder'): ('Exact TOP', ('hanging',)),..} - тут вже зббергіаєсмо комбінації
        rest = []
        

        for p in keywords_tuples:
            if p not in keywords_total_dict.keys():
                rest.append(" ".join(p))

        total_result = defaultdict(list)
        for k, v in keywords_total_dict.items():
            total_result[v].append(" ".join(k)) # ('Exact TOP', ('glass',)): ['red glass hummingbird feeder'], ('Exact LOW', ('small',)): ['small hummingbird feeders for outdoors'], ('Exact TOP', ('large',)): ['large hummingbird feeders for outdoors'], - тут збираємо до купи кейвордси
        
        # SEED, Exact STR Top, Exact STR Low
        if len(seed) >= 1:
            split_and_append("SEED", phrase, "", values["seed"], seed, 10000, "SEED")

        if len(str_low) >= 1:
            split_and_append(
                "Exact",
                phrase,
                "",
                values["str_low"],
                str_low,
                campaign_count,
                "STR Low",
            )
        # if len(variations) >= 1:
        #     split_and_append(
        #         "Variation",
        #         phrase,
        #         "",
        #         values["variation"],
        #         variations,
        #         campaign_count,
        #         "Variation",
        #     )
        if len(broad) >= 1:
            split_and_append(
                "Broad", phrase, "", values["broad"], broad, 10000, "Broad"
            )
        if len(words) >= 1:
            split_and_append(
                "Words", phrase, "", values["words"], words, 10000, "Words"
            )
        if len(brand_def) >= 1:
            split_and_append(
                "Brand Defense",
                phrase,
                "",
                values["brand_def"],
                brand_def,
                10000,
                "Brand Defense",
            )
        split_and_append(
            "Self Targeting",
            phrase,
            "",
            values["adv_asin"],
            adv_asin,
            10000,
            "Self Targeting",
        )

        # Other categories
        for q in other:
            if q in total_result:
                if len(total_result[q]) >= 1:
                    if "exact top" in q[0].lower():
                        # print(f"values['exact_top']: {total_result[q]}")
                        split_and_append(
                            "Exact",
                            phrase,
                            q[1][0],
                            values["exact_top"],
                            total_result[q],
                            campaign_count,
                            "Exact Top",
                        )

        for q in other:
            if q in total_result:
                if len(total_result[q]) >= 1:
                    if (
                        "exact" in q[0].lower()
                        and "low" not in q[0].lower()
                        and "top" not in q[0].lower()
                    ):
                        split_and_append(
                            "Exact",
                            phrase,
                            q[1][0],
                            values["exact"],
                            total_result[q],
                            campaign_count,
                            "Exact",
                        )

        for q in other:
            if q in total_result:
                if len(total_result[q]) >= 1:
                    if "exact low" in q[0].lower():
                        split_and_append(
                            "Exact",
                            phrase,
                            q[1][0],
                            values["exact_low"],
                            total_result[q],
                            campaign_count,
                            "Exact Low",
                        )
        if len(rest) >= 1:
            split_and_append(
                "Exact",
                phrase,
                "",
                values["exact_other"],
                rest,
                campaign_count,
                "Exact Other",
            )

        for q in other:
            # print(f"q from other: {q}, q[0]:{q[0]}  q[1][0]: {q[1][0]}, values['brands']: {values['brands']}, total_result[q]: {total_result[q]}")
            if q in total_result:
                if "brands" in q[0].lower():
                    if len(total_result[q]) >= 1:
                        split_and_append(
                            q[0],
                            phrase,
                            q[1][0],
                            values["brands"],
                            total_result[q],
                            campaign_count,
                            q[0],
                        )

        for q in other:
            if q in total_result:
                if "variation" in q[0].lower():
                    if len(total_result[q]) >= 1:
                        split_and_append(
                            q[0],
                            phrase,
                            q[1][0],
                            values["variation"],
                            total_result[q],
                            campaign_count,
                            q[0],
                        )
        
        # PAT Negatives
        pat_negatives = []
        # print(f"tpas: {tpas}")
        for p in tpas:
            pat_negatives.extend(p[1:])
            if len(p[1:]) >= 1:
                split_and_append(
                    "PAT", phrase, p[0], values[p[0].lower().split()[0]], p[1:], 500, f"PAT", p[0].lower()
                )

        # Category
        for p in category:
            if len(p[1:]) >= 1:
                split_and_append(
                    "Category",
                    phrase,
                    "",
                    values["category"],
                    p[1:],
                    campaign_count,
                    "Category",
                )

        # Auto Negatives
        for type_ in ["Close", "Loose", "Subs", "Compl"]:
            split_and_append(
                "Auto",
                phrase,
                "",
                values["auto_negatives"],
                [],
                10000,
                f"Auto Negatives {type_}",
            )

        # Auto
        for type_ in ["Close", "Loose", "Subs", "Compl"]:
            split_and_append(
                "Auto", phrase, "", values["auto"], [], 10000, f"Auto {type_}"
            )

        # NegativePhrases
        # if len(negative) >= 1:
        split_and_append(
            "NegativePhrases",
            phrase,
            "",
            {"scu": "", "bid": ""},
            negative,
            100000,
            "NegativePhrases",
        )

        # # NegativeExacts
        # negative_exacts = keywords + seed + str_low + launched

        # split_and_append('NegativeExacts', phrase, 'NegativeExacts', {
        #                  'scu': '', 'bid': ''}, negative_exacts, 10000, "NegativeExacts")

        # NegativePATs
        # if len(pat_negatives) >= 1:
        # split_and_append(
        #     "NegativePATs",
        #     phrase,
        #     "",
        #     {"scu": "", "bid": ""},
        #     pat_negatives,
        #     100000,
        #     "NegativePATs",
        # )

    worksheet_objs = table.worksheets()
    worksheets_list = []
    for worksheet in worksheet_objs:
        worksheets_list.append(worksheet.title)

    if range_name + " (clusters)" not in worksheets_list:
        table.add_worksheet(title=range_name + " (clusters)", rows="100", cols="20")

    df = pd.DataFrame(list_total).T

    clusters = table.worksheet(range_name + " (clusters)")
    num_rows, num_cols = df.shape
    clusters.resize(rows=num_rows, cols=num_cols)
    clusters.clear()

    clusters.update("C1", pd.DataFrame(list_total).T.values.tolist())

    upload_campaign_to_db(request)


def extract_text(input_string):

    match = re.search(r"\(([^)]+)\)", input_string)
    if match:
        return match.group(1) + input_string.split(")")[1]
    return None


def upload_campaign_to_db(request):
    user_id = request.user.id

    campaigns = list()
    filter_campaign_names = list()
    # print(f"campaign_names in cluster: {campaign_names}")
    unique_campaign_names = list(dict.fromkeys(campaign_names))

    for campaign_name in unique_campaign_names:
        filter_campaign_names.append(extract_text(campaign_name))

    unique_campaign_names = list(dict.fromkeys(filter_campaign_names))
    Campaign.objects.filter(user_id=user_id).delete()

    for campaign_name in unique_campaign_names:
        campaigns.append(Campaign(name=campaign_name, user_id=user_id))

    Campaign.objects.bulk_create(campaigns)


