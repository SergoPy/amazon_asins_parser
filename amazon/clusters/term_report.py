import pandas
from webscraper.settings import MEDIA_ROOT


class SearchTermReport:
    MONTHS = {
        '01': 'january',
        '02': 'february',
        '03': 'march',
        '04': 'april',
        '05': 'may',
        '06': 'june',
        '07': 'july',
        '08': 'august',
        '09': 'september',
        '10': 'october',
        '11': 'november',
        '12': 'december'
    }
    TERM_REPORT_FILENAME = f'{MEDIA_ROOT}term_report.xlsx'
    CATEGORIES_KEYS = {
                  'impression': ('Increased Impressions', 'Decreased Impressions'),
                  'click': ('Increased Clicks', 'Decreased Clicks'),
                  'ctr': ('Increased CTR', 'Decreased CTR'),
                  'spend': ('Increased Spend', 'Decreased Spend'),
                  'sales': ('Increased Sales', 'Decreased Sales'),
                  'acos': ('Increased ACOS', 'Decreased ACOS')
    }
    DEFAULT_CAMPAIGN = 'New'
    COLUMNS = ['Keywords', 'Date', 'Company Name', 'Impressions', 'Clicks', 'CTR', 'CPC', 'Spend', 'Sales', 'ACOS',
               'Date', 'Company Name', 'Impressions', 'Clicks', 'CTR', 'CPC', 'Spend', 'Sales', 'ACOS']

    def __init__(self, file1: str, file2: str, products=None, check_all=True):
        if products is None:
            products = {}
        self.file1 = file1
        self.file2 = file2
        self.products = products
        self.check_all = check_all
        self.result_data = self._result_data_init()
        self.writer = self._get_writer()

    def _get_writer(self) -> pandas.ExcelWriter:
        return pandas.ExcelWriter(self.TERM_REPORT_FILENAME, engine='xlsxwriter')

    @staticmethod
    def _date_to_str(datetime: str) -> tuple:
        split_data = datetime.split()[0].split('-')
        return split_data[1], split_data[2]

    def _format_datetime(self, start_date: str, end_date: str):
        start_month, start_day = self._date_to_str(start_date)
        end_month, end_day = self._date_to_str(end_date)
        if start_month == end_month:
            return f'{self.MONTHS[start_month]} {start_day}-{end_day}'
        else:
            return f'{self.MONTHS[start_month]} {start_day}-{self.MONTHS[end_month]} {end_day}'

    def _write_results(self):
        for category in self.result_data:
            data = self.result_data[category]
            data = pandas.DataFrame(data)
            if len(data) and category == self.DEFAULT_CAMPAIGN:
                data.to_excel(self.writer, sheet_name=category, index=False,
                              header=self.COLUMNS[:10])
            elif len(data):
                data.to_excel(self.writer, sheet_name=category, index=False,
                              header=self.COLUMNS)
        self.writer.save()

    def _result_data_init(self) -> dict:
        data_init = {
            self.DEFAULT_CAMPAIGN: []
        }
        for key in self.CATEGORIES_KEYS:
            increased, decreased = self.CATEGORIES_KEYS[key]
            data_init[increased] = []
            data_init[decreased] = []
        return data_init

    @staticmethod
    def _scan_xlsx_file(file: str) -> pandas.DataFrame:
        data = pandas.read_excel(file)
        return pandas.DataFrame(data)

    @staticmethod
    def _calculate_values(data1: dict, data2: dict) -> dict:
        data1['impression'] += data2['impression']
        data1['click'] += data2['click']
        data1['spend'] += data2['spend']
        data1['sales'] += data2['sales']

        clicks = data1['click']
        spend = data1['spend']
        data1['ctr'] = clicks / data1['impression'] * 100 if data1['impression'] else 0
        data1['cpc'] = spend / clicks if clicks else 0
        data1['acos'] = spend / data1['sales'] if data1['sales'] else 0
        return data1

    def _manage_data(self, table_data: pandas.DataFrame) -> dict:
        result = {product_data[2]: [] for product_data in table_data.values}

        for product_data in table_data.values:
            product = product_data[2]
            result[product].append(product_data)

        for key in result:
            products_data = result[key]
            products_values = {}
            for data in products_data:
                search_term = data[8]
                start_date, end_date = str(data[0]), str(data[1])
                analytic_data = {
                    'search_term': search_term,
                    'date': self._format_datetime(start_date, end_date),
                    'name': data[4],
                    'impression': data[9],
                    'click': data[10],
                    'ctr': data[11],
                    'cpc': data[12],
                    'spend': data[13],
                    'sales': data[14],
                    'acos': data[15]
                }
                product_data = products_values.get(search_term)
                if product_data:
                    products_values[search_term] = self._calculate_values(product_data, analytic_data)
                else:
                    products_values[search_term] = analytic_data
            result[key] = products_values
        return result

    @staticmethod
    def _sort_data(table_data: pandas.DataFrame) -> pandas.DataFrame:
        table_data.sort_values(by=['Portfolio name', 'Customer Search Term'],
                               ascending=[True, True], inplace=True)

        return table_data

    def _get_analytic_data(self, table_data_1: pandas.DataFrame, table_data_2: pandas.DataFrame) -> tuple:
        sort_data_1, sort_data_2 = self._sort_data(table_data_1), self._sort_data(table_data_2)
        analytic_data1, analytic_data2 = self._manage_data(sort_data_1), self._manage_data(sort_data_2)
        return analytic_data1, analytic_data2

    def _analysing_values(self, values1: dict, values2: dict) -> None:
        data_row_1 = [values1[key] for key in values1]
        data_row_2 = [values2[key] for key in values2]
        result_row = data_row_1 + data_row_2[1:]
        write_counter = 0
        for key in self.CATEGORIES_KEYS:
            increased, decreased = self.CATEGORIES_KEYS[key]
            if values1[key] < values2[key]:
                self.result_data[increased].append(result_row)
                write_counter += 1
            elif values1[key] > values2[key]:
                self.result_data[decreased].append(result_row)
                write_counter += 1
        if not write_counter:
            self.result_data[self.DEFAULT_CAMPAIGN].append(data_row_1)

    def _analysing_data(self, data1: dict, data2: dict) -> None:
        for product in data1:
            for search_term in data1[product]:
                value1 = data1[product][search_term]
                product = self.products[product] if product in self.products else product
                if self.check_all or product in self.products:
                    try:
                        value2 = data2[product][search_term]
                    except KeyError:
                        value2 = value1
                    self._analysing_values(value1, value2)

    def run(self):
        file_data_1 = self._scan_xlsx_file(self.file1)
        file_data_2 = self._scan_xlsx_file(self.file2)
        file_data1, file_data2 = self._get_analytic_data(file_data_1, file_data_2)
        self._analysing_data(file_data1, file_data2)
        self._write_results()


def create_term_report(file1: str, file2: str, products: bool, all_products: bool):
    term_report = SearchTermReport(file1, file2, products, all_products)
    term_report.run()
