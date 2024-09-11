def google_sheets_clusters(table_link, values):
    # print(f"values: {values}")
    spreadsheet_id = get_table_id(table_link)

    with open('/clusters/apikey.json', 'r') as file:
        content = file.read()
        print(content)
    gc = gspread.service_account(filename='apikey.json')
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