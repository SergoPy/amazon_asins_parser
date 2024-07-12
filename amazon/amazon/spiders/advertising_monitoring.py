import re
import string
import time
from copy import deepcopy

from datetime import datetime
import gspread
import scrapy
from amazon.utils import indexes_to_a1
from amazon.models import AdvertisingMonitoring
from random_user_agent.params import HardwareType, SoftwareName, OperatingSystem, Popularity
from random_user_agent.user_agent import UserAgent

from uploaders.amazon_seller_scanner import AdvertisingScanner


class AdvertisingScannerSpider(scrapy.Spider):
    name = 'advertising_monitoring'
    ADVERTISING_CAMPAIGNS = ['SB', 'SD', 'SP', 'TPK', 'Total']

    def __init__(self,
                 asins: str,
                 google_sheet_link: str,
                 apikey_filepath: str,
                 category: str,
                 **kwargs
                 ):

        super().__init__(self, **kwargs)
        self.apikey_filepath = apikey_filepath
        self.asins = self._get_asins(asins)
        self.base_url = kwargs['base_url']
        self.base_search_url = f'{self.base_url}s?k='
        self.base_item_url = f'{self.base_url}dp/'
        self.category = category
        self.cookie = kwargs['country_cookie']
        self.table_url = google_sheet_link
        self.user_agents = self._get_user_agents()
        self.asins_data = AdvertisingMonitoring()

        self.asins_counter = len(self.asins)
        self.kwargs = kwargs


    @staticmethod
    def _get_asins(asins: str) -> list:
        return list(map(lambda x: x.strip('()'), asins.split()))

    def _get_item_url(self, item_asin: str) -> str:
        return self.base_item_url + item_asin

    @staticmethod
    def _get_user_agents():
        popularity = [Popularity.POPULAR.value]
        hardware_types = [HardwareType.COMPUTER.value]
        software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
        operating_systems = [OperatingSystem.MACOS.value, OperatingSystem.LINUX.value,
                             OperatingSystem.WINDOWS.value]

        user_agents = UserAgent(
            popularity=popularity, hardware_types=hardware_types,
            software_names=software_names, operating_systems=operating_systems,
            limit=100
        )
        return user_agents

    def _get_headers(self):
        return {
            'User-Agent': self.user_agents.get_random_user_agent(),
            'Cookie': self.cookie
        }

    def _get_position_in_category(self, bsr: str) -> str:
        position = re.compile(rf'#(.*) in {self.category}').findall(bsr)[0]
        return position.strip(string.ascii_lowercase + ' ')

    def _get_worksheet(self):
        service = gspread.service_account(filename=self.apikey_filepath)
        table = service.open_by_url(self.table_url)
        worksheet_name = self.kwargs.get('seller_name')
        worksheet = [worksheet for worksheet in table.worksheets() if worksheet.title == worksheet_name][0]

        return worksheet

    def _get_coords(self, worksheet, cell_name: str, len_of_date: int) -> str:
        str_date = self._get_str_date()
        row = worksheet.find(cell_name).row + 1
        col = worksheet.findall(str_date)[0].col

        return f'{indexes_to_a1(row, col)}:{indexes_to_a1(row + len_of_date, col)}'


    @staticmethod
    def _get_str_date():
        today = datetime.now()
        day, month = today.strftime('%d'), today.strftime('%B')[:3]
        return f'{day} {month}'

    def _write_statistic(self, monitoring_data) -> None:
        worksheet = self._get_worksheet()
        for campaign_name in self.ADVERTISING_CAMPAIGNS:
            data = monitoring_data.statistic.get(f'{campaign_name.lower()}_data')
            if data:
                coords = self._get_coords(worksheet, campaign_name, len(data))
                worksheet.update(coords, data, value_input_option = 'USER_ENTERED')



    def spider_closed(self, _):
        with AdvertisingScanner(self.asins_data, **self.kwargs) as scanner:
            monitoring_data = scanner.run()
            self._write_statistic(monitoring_data)

    def start_requests(self):
        for asin in self.asins:
            yield scrapy.Request(self._get_item_url(asin), self.item_data_scanner, headers=self._get_headers(),
                                 cb_kwargs={'base_asin': asin}
                                 )

    def item_data_scanner(self, response, base_asin: str):
        asins = [base_asin]
        brand_href = response.css('#bylineInfo::attr(href)').get()
        if brand_href:
            brand_name = brand_href.split('/')[1]
            brand_name = brand_href.split('/')[2] if brand_name == 'stores' else brand_name
        else:
            brand_name = 'unknown'

        item_details = response.css('[id="detailBulletsWrapper_feature_div"]')
        bsr = item_details.css('ul.detail-bullet-list::text').get()
        position = self._get_position_in_category(bsr)

        variations_body = response.css('ul.a-button-toggle-group')

        if variations_body:
            variations = variations_body.css('li::attr(data-defaultasin)').getall()
            variation_asins = [asin for asin in variations if asin]
            asins += variation_asins

        self.asins_data.append_asin_data(base_asin, brand_name, position)
