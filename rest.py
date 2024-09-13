from datetime import date


auto_neg_items = ['FBA-ST-02-11', 'BAL-1-BC']
keyword_negatives = ['cancer awareness sticker',
                     'cancer fundraising',
                     'cancer ribbon sticker',
                     'cancer sticker',
                     'child cancer awareness',
                     'childhood cancer',
                     'childhood cancer awareness',
                     'childhood cancer awareness decoration',
                     'childhood cancer awareness item',
                     'childhood cancer awareness month',
                     'childhood cancer awareness ribbon',
                     'childhood cancer awareness sticker',
                     'childhood cancer ribbon',
                     'go gold childhood cancer',
                     'gold cancer ribbon',
                     'gold ribbon child cancer awareness',
                     'gold ribbon sticker',
                     'gold ribbon sticker childhood cancer',
                     'gold ribbon childhood cancer',
                     'pediatric cancer awareness',
                     'ribbon sticker',
                     'yellow ribbon sticker',
                     'anti drug sticker',
                     'drug awareness item',
                     'drug awareness ribbon',
                     'drug free red ribbon week',
                     'drug sticker',
                     'drug sticker laptop',
                     'drug awarness',
                     'just say no drug sticker',
                     'no drug sticker',
                     'red drug awareness',
                     'red ribbon drug awareness',
                     'red ribbon week sticker roll',
                     'red ribbon week swag',
                     'say no drug',
                     'say no drug sticker',
                     'sticker drug',
                     'apparel pin breast cancer awareness',
                     'breast cancer awareness brooch',
                     'breast cancer awareness pink ribbon pin',
                     'breast cancer awareness pin small',
                     'breast cancer awareness survivor sash',
                     'breast cancer badge pin',
                     'breast cancer brooch',
                     'breast cancer button',
                     'breast cancer pin',
                     'breast cancer pink ribbon pin',
                     'breast cancer pin man',
                     'breast cancer ribbon pin',
                     'breast cancer survivor pin',
                     'cancer pink pin',
                     'cancer ribbon pink',
                     'pink breast cancer accessorie woman',
                     'pink breast cancer ribbon pin',
                     'pink pin breast cancer',
                     'pink ribbon breast cancer awareness lapel pin',
                     'pink ribbon breast cancer pin',
                     'pink ribbon pin',
                     'pink ribbon pin breast cancer']
phrases_negatives = []
auto_neg_data = ['Gold Ribbon Stickers | Auto Negatives Close ',
                 'auto',
                 'FBA-ST-02-11, BAL-1-BC',
                 '0.792']
cmp_ending = 'sp'
target_asin = 'B010R6FDMG'
title = ['Gold Ribbon Stickers']


total_auto_neg_len = 4 + len(auto_neg_items) + \
    len(keyword_negatives) + len(phrases_negatives) + 4

none = [None] * total_auto_neg_len

data = [
    ['Sponsored Products'] * total_auto_neg_len,  # 1 - 70
    ['Campaign'] + ['Bidding Adjustment'] * 2 + ['Ad Group'] + ['Product Ad'] * len(auto_neg_items) +
    ['Product Targeting'] * 4 + ['Campaign Negative Keyword'] * \
    (len(keyword_negatives) + len(phrases_negatives)),  # 2 - 70
    ['Create'] * total_auto_neg_len,  # 3 -70
    [title[0] + target_asin + \
     f' -{cmp_ending}'] * total_auto_neg_len,  # 4 -70
    [None] * 3 + [auto_neg_data[1]] * 2 + [None] * 4 + \
    [auto_neg_data[1]] * (total_auto_neg_len - 9),  # 5 - 70
    none,  # 6
    none,  # 7
    none,  # 8
    none,  # 9
    [auto_neg_data[0] + f' -{cmp_ending}'] + \
    [None] * (total_auto_neg_len - 1),  # 10 - 70
    [None] * 3 + [auto_neg_data[1]] + [None] * \
    (total_auto_neg_len - 4),  # 11 - 70
    none,  # 12
    [None] * 3 + [auto_neg_data[1]] * (1 + len(auto_neg_items) + 4) + [None] * (
        total_auto_neg_len - 8 - len(auto_neg_items)),  # 13 - 70
    none,  # 14
    [str(date.today()).replace('-', '')] + [None] * \
    (total_auto_neg_len - 1),  # 15 - 70
    none,  # 16
    ['AUTO'] + [None] * (total_auto_neg_len - 1),  # 17 -70
    ['enabled'] + [None] * 2 + ['enabled'] * 2 + [1, 1, 1, 1] + ['enabled'] * \
    (total_auto_neg_len - 9),  # 18 --------------------------------------------72 -------70
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
    [None] * (4 + len(auto_neg_items)) + [1, 1, 1, 1] + [None] * \
    (total_auto_neg_len - 8 - len(auto_neg_items)),  # 28 - 70
    [None] * (4 + len(auto_neg_items)) + list(keyword_negatives) + \
    list(phrases_negatives),  # 29 - 70
    [None] * (4 + len(auto_neg_items)) + ['negativeExact'] * len(keyword_negatives) + \
    ['negativePhrase'] * len(phrases_negatives),  # 30 - 70
    ['Dynamic bids - down only'] * 3 + [None] * \
    (total_auto_neg_len - 3),  # 31 - 70
    [None, 'placementProductPage', 'placementTop'] + \
    [None] * (total_auto_neg_len - 3),  # 32 - 70
    [None, 0, 0] + [None] * (total_auto_neg_len - 3),  # 33 - 70
    [None] * (4 + len(auto_neg_items)) + ['close-match', 'loose-match', 'substitutes',
                                          'complements'] + [None] * (total_auto_neg_len - 8 - len(auto_neg_items)),  # 34
    none, none, none, none, none, none, none, none, none, none, none, none
]


def calculate_array_size(data):
    # Обчислення довжини кожного вкладеного списку
    lengths = [len(row) for row in data]

    # Кількість рядків - це кількість вкладених списків
    num_rows = len(data)

    # Кількість стовпців - максимальна довжина серед вкладених списків
    num_cols = max(lengths) if lengths else 0

    return num_rows, num_cols


# Виклик функції
num_rows, num_cols = calculate_array_size(data)

print(len(COLUMNS))

print(f"Розмір масиву: {num_rows} x {num_cols}")
