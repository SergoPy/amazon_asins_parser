import pandas as pd
import httplib2
import gspread
from googleapiclient import discovery



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


keywords = []
seed = []
launched = []

gc = gspread.service_account(filename='apikey.json')
table = gc.open_by_key("12UfK4uiYWEaVas5d2EE4S13yTEeFDV0Z5yeJA2Q02lI")
range_name = table.sheet1.title
df_total = get_data_frame('AIzaSyApx1yQj6lKf_szFGXrw9euKcrFPqxR5VY',
                          "12UfK4uiYWEaVas5d2EE4S13yTEeFDV0Z5yeJA2Q02lI", range_name)
for k in df_total.T.values:
    if k[0].lower() == 'launched':
        launched = [x for x in k[1:] if x is not None and x != '']
    elif k[0].lower() == 'keywords':
        keywords = [x for x in k[1:]
                    if x is not None and x != '' and x not in launched]
    elif k[0].lower() == 'seed':
        seed = [x for x in k[1:] if x is not None and x !=
                '' and x not in launched]
keywords_filtered = list((set(keywords) - set(seed)))
# print(f"keywords_filtered: {len(keywords_filtered)}")
                

# Залишаємо тільки унікальні значення у кожному списку
A_unique = list(set(keywords_filtered))

print(f"len: {len(A_unique)}")


# def count_sentences_with_word(word, sentence_list):
#     word_lower = word.lower()
#     count = sum(1 for sentence in sentence_list if word_lower in sentence.lower())
#     words = [sentence for sentence in sentence_list if word_lower in sentence.lower()]
#     return count, words

# word_to_search = "gift"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "halloween"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "goth"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "coffin"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "witch"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "spooky"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")

# word_to_search = "horror"  
# count, words = count_sentences_with_word(word_to_search, A_unique)

# print(f"Кількість речень, які містять слово '{word_to_search}': {count}; {words}")