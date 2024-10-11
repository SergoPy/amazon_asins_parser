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

    def get_cell(self, row, col):
        return self.worksheet.cell(row, col)

    def get_coords(self, col):
        # print(f"tut col: {col}")
        row = len(self.worksheet.col_values(col)) + 1
        # print(f"tut row: {row}")
        return [row, col]

    def update_cell(self, row, col, value):
        self.worksheet.update_cell(row, col, value)

    def update(self, diapason, value_list):
        print(f"diapason: {diapason}; value_list: {value_list}")
        self.worksheet.update(diapason, value_list,
                              value_input_option='USER_ENTERED')

    def find_cell(self, value):
        cells = self.worksheet.get_all_cells()
        for cell in cells:
            if value in str(cell.value):
                return cell
        return None

    def get_cord_by_name(self, value):
        return self.get_coords(self.find_cell(value).col)

    def clear_from_column(self, start_col):
        all_values = self.worksheet.get_all_values()
        total_cols = max([len(row) for row in all_values])
        total_rows = len(all_values)
        range_to_clear = f"{gspread.utils.rowcol_to_a1(1, start_col)}:{gspread.utils.rowcol_to_a1(total_rows, total_cols)}"
        self.worksheet.batch_clear([range_to_clear])

        print(f"total_rows: {total_rows}; total_cols: {total_cols}; start_col: {start_col}; range_to_clear: {range_to_clear}")


    def ensure_columns(self, need):
        total_cols = self.worksheet.col_count #64

        if total_cols < need:
            cols_to_add = need - total_cols
            self.worksheet.add_cols(cols_to_add)