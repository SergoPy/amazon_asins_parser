from copy import deepcopy
from datetime import datetime


class AsinsData:

    def __init__(
            self,
            asins: list,
            brand: str,
            position: str
    ):

        self.asins = asins
        self.brand = brand
        self.is_variational = len(self.asins) > 1
        self.position = position

        self.stock = None
        self.unit_session_percentage = None
        self.ordered_product_sales = None
        self.ordered_product_sales_b2b = None
        self.sessions_total = None
        self.sessions_total_b2b = None

    def append_stock_data(self, stock) -> None:
        self.stock = stock

    def append_business_report_data(self, unit_session_percentage, ordered_product_sales,
                                    ordered_product_sales_b2b, sessions_total, sessions_total_b2b) -> None:

        self.unit_session_percentage = unit_session_percentage
        self.ordered_product_sales = ordered_product_sales
        self.ordered_product_sales_b2b = ordered_product_sales_b2b
        self.sessions_total = sessions_total
        self.sessions_total_b2b = sessions_total_b2b

class AdvertisingMonitoring:
    ADVERTISING_CAMPAIGNS = ['SB', 'SD', 'SP', 'TPK', 'Total']

    def __init__(self):
        self.asins_data = []
        self.metrics = {}
        self.statistic = {}


    def append_asin_data(self, *args):
        self.asins_data.append(AsinsData(*args))

    def _get_total_metric_value(self, key):
        return sum(list(map(lambda x: x.get(key, 0), self.metrics.values())))

    def _get_total_statistic_data(self) -> list:
        business_report = self.asins_data[0]

        acos = self._get_total_metric_value('ACOS')
        sales = self._get_total_metric_value('Sales')
        spend = self._get_total_metric_value('Spend')

        total_sessions = business_report.sessions_total + business_report.sessions_total_b2b
        total_sales = business_report.ordered_product_sales + business_report.ordered_product_sales_b2b
        total_cvr = business_report.unit_session_percentage
        ad_cvr = 0
        ppc_sales = sales / total_sales * 100

        brand_names = [item.position for item in self.asins_data]

        return [acos, total_sessions, total_sales, total_cvr, ad_cvr, sales, spend, ppc_sales,
                total_cvr, total_sales, ppc_sales] + brand_names

    def _get_statistic_data_for_campaign(self, metric_data: dict) -> list:
        acos, sales = metric_data.get('ACOS'), metric_data.get('Sales')
        ad_cvr = metric_data.get('Clicks', 0) / metric_data.get('Orders', 1) * 100
        campaign_spend = metric_data.get('Spend')
        total_spend = self._get_total_metric_value('Spend')
        ppc_spend = campaign_spend / total_spend * 100

        return [acos, ad_cvr, sales, campaign_spend, ppc_spend]

    def get_statistic(self):
        for campaign in self.metrics:
            for adv_campaign in self.ADVERTISING_CAMPAIGNS:
                if adv_campaign in campaign:
                    self.statistic[adv_campaign] = self._get_statistic_data_for_campaign(self.metrics[campaign])
        self.statistic['Total'] = self._get_total_statistic_data()

    def append_metric(self, campaign, metric_name, metric_value) -> None:
        if campaign not in self.metrics:
            self.metrics[campaign] = {}

        self.metrics[campaign][metric_name] = float(metric_value)


class MonitoringAsins:
    def __init__(self, keywords: list):
        self.asins = []
        self.keywords = keywords
        self.statistic = {}

    def append_asins(self, asins: list, brand_name: str) -> None:
        for i in range(len(self.asins)):
            if self.asins[i]['brand_name'] == brand_name:
                self.asins[i]['asins'] += asins
                return

        self.asins.append({
            'asins': asins,
            'brand_name': brand_name
        })

    def sort_asins_data(self, correct_priority: list) -> None:
        sorted_asins = []
        for asin in correct_priority:
            for asin_data in self.asins:
                if asin in asin_data['brand_name']:
                    sorted_asins.append(asin_data)
        self.asins = sorted_asins

    def append_statistic(self, keyword: str, brand_name: str, data: list) -> None:
        for i in (0, 1):
            self.statistic[keyword][brand_name][i][0] += data[i][0]
            if data[i][1] and not self.statistic[keyword][brand_name][i][1]:
                self.statistic[keyword][brand_name][i][1] = self.statistic[keyword][brand_name][i][0]
        for j in (2, 3):
            self.statistic[keyword][brand_name][j] = self.statistic[keyword][brand_name][j] or data[j][1]

    def create_statistic(self):
        brand_data = [[0, 0], [0, 0], False, False]
        keyword_data = {asins_data['brand_name']: deepcopy(brand_data) for asins_data in self.asins}
        statistic = {keyword: deepcopy(keyword_data) for keyword in self.keywords}
        self.statistic = statistic

    def get_brands(self):
        return [asins_data['brand_name'] for asins_data in self.asins]

    @staticmethod
    def check_sb_value(status: bool) -> str:
        return 'yes' if status else 'no'

    @staticmethod
    def complete_list(list1: list, list2: list) -> list:
        none_len = len(list1) - len(list2)
        return list2 + ['' for _ in range(none_len)]

    def get_table_header(self) -> tuple:
        date = datetime.today().strftime('%d.%m')
        brands = self.get_brands()
        headers = [date] + self.complete_list(brands, ['Organic']) + self.complete_list(brands, ['Advertising'])
        brands_header = [''] + brands * 2
        return headers, brands_header

    def format_statistic(self):
        result = []
        header, brands_header = self.get_table_header()
        result.append(header)
        result.append(brands_header)
        for keyword in self.statistic:
            adv_data = []
            org_data = []
            sb_data = ['SB']
            sbv_data = ['SBV']
            for brand in self.statistic[keyword]:
                data = self.statistic[keyword][brand]
                org_data.append(data[0][1])
                adv_data.append(data[1][1])
                sb_data.append(self.check_sb_value(data[2]))
                sbv_data.append(self.check_sb_value(data[3]))
            main_data = [keyword] + org_data + adv_data
            result.append(main_data)
            result.append(self.complete_list(main_data, sb_data))
            result.append(self.complete_list(main_data, sbv_data))
        return result
