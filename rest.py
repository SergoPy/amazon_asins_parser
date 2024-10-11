import gspread


class GoogleSheetsApi:
    def __init__(self, table_id, file_path):
        self.table_id = table_id
        self.apikey_file_path = file_path
        self.connection = self.get_api_connection()
        self.worksheet = self.get_table_by_id().sheet1

    def get_api_connection(self):
        return gspread.service_account(filename=self.apikey_file_path)

    def get_table_by_id(self):
        return self.connection.open_by_key(self.table_id)
    
    def ensure_columns(self, need):
        total_cols = self.worksheet.col_count #64

        if total_cols < need:
            cols_to_add = need - total_cols
            self.worksheet.add_cols(cols_to_add)

gs = GoogleSheetsApi("1F6LFwyc4Zbjmg_WrSljbJIQ6gfycaPR_eoRBYFuS71k", "apikey.json")

gs.ensure_columns(16, 70)