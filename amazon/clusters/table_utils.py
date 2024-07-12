import gspread


def get_table_name(table_link):
    authorization = gspread.service_account('clusters/apikey.json')
    table = authorization.open_by_url(table_link)
    return table.title
