import re
import time
from copy import deepcopy

from datetime import datetime
import gspread
import scrapy
from amazon.utils import indexes_to_a1
from random_user_agent.params import HardwareType, SoftwareName, OperatingSystem, Popularity
from random_user_agent.user_agent import UserAgent


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


class AsinsScannerSpider(scrapy.Spider):
    MONTHS = {
        '01': 'January',
        '02': 'February',
        '03': 'March',
        '04': 'April',
        '05': 'May',
        '06': 'June',
        '07': 'July',
        '08': 'August',
        '09': 'September',
        '10': 'October',
        '11': 'November',
        '12': 'December'
    }   
    name = 'asins_monitoring'
    URL_PAGE_PART = '&page='

    def __init__(self,
                 personal_asin: str,
                 competitor_asins: str,
                 keywords: str,
                 product_name: str,
                 google_sheet_link: str,
                 apikey_filepath: str,
                 **kwargs
                 ):

        super().__init__(self, **kwargs)

        self.base_url = kwargs['base_url']
        self.base_search_url = f'{self.base_url}s?k='
        self.base_item_url = f'{self.base_url}dp/'
        self.personal_asin = personal_asin.strip('\n\r')
        self.product_name = product_name
        self.competitor_asins = self._get_competitor_asins(competitor_asins)
        self.keywords = keywords.split('\r\n')
        self.scan_pages_data = self.get_scan_pages(self.keywords)
        self.monitoring_asins = MonitoringAsins(self.keywords)
        self.apikey_file_path = apikey_filepath
        self.asins_counter, self.pages_counter = self.get_counters()
        self.user_agents = self.get_user_agents()
        self.cookie = kwargs['country_cookie']
        self.table = google_sheet_link

    @staticmethod
    def _get_competitor_asins(asins: str) -> list:
        return list(map(lambda x: x.strip(), asins.split('\r\n')))

    @staticmethod
    def close(spider, reason):
        spider.spider_closed(reason)

    def spider_closed(self, _):
        self.write_statistic()
    
    @staticmethod
    def get_user_agents():
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

    def get_scan_pages(self, keywords: list) -> list:
        scan_pages = []
        for request_phrase in keywords:
            phrase_format = request_phrase.replace(' ', '+')
            scan_pages.append((request_phrase, f'{self.base_search_url}{phrase_format}'))
        return scan_pages

    def get_counters(self) -> tuple:
        asins_counter = len(self.competitor_asins) + 1
        pages_counter = len(self.scan_pages_data)
        return asins_counter, pages_counter

    def get_item_link(self, asin: str) -> str:
        return f'{self.base_item_url}{asin}'

    def get_next_url(self, url: str, index: int) -> str:
        return f'{url.split("&")[0]}{self.URL_PAGE_PART}{index}'

    def _month_init(self, worksheet, month: str) -> tuple:
        text_color = {"red": 0, "green": 0, "blue": 0}
        month_color = {"red": 0.99, "green": 0.89, "blue": 0.6}

        number_of_rows = len(worksheet.col_values(10)) + 2
        time.sleep(1)
        cell = number_of_rows, 1
        values_update_diapason = f'{indexes_to_a1(*cell)}:{indexes_to_a1(*cell)}'
        worksheet.update(values_update_diapason, [[month]], value_input_option='USER_ENTERED')
        #worksheet.merge_cells(f'{indexes_to_a1(*cell)}:{number_of_rows, 5}')

        self.format_worksheet(
                    worksheet,
                    (cell, (number_of_rows, 7)),
                    text_color, month_color, 14
        )
        time.sleep(1)
        return cell

 
    def _get_write_cords(self, worksheet) -> tuple:
        month = self.MONTHS[datetime.today().strftime('%m')]
        try:
            month_cell = worksheet.find(month)
            time.sleep(1)
            row, col = month_cell.row, month_cell.col
            number_of_columns = len(worksheet.row_values(row))
            col = number_of_columns + 8
            return row, col

        except Exception:
            time.sleep(2)
            row, col = self._month_init(worksheet, month)
            worksheet.merge_cells(f'{indexes_to_a1(row, col)}:{indexes_to_a1(row, col + 7)}')
            time.sleep(1)
            return row, col + 9
             
    @staticmethod
    def get_paint_row_params(bg_color: dict, text_color: dict, font_size) -> dict:
        return {
            "backgroundColor": bg_color,
            "horizontalAlignment": "CENTER",
            "textFormat": {
                "foregroundColor": text_color,
                "fontSize": font_size,
                "bold": False
            }
        }
                                                       
    def format_worksheet(self, worksheet, coords: tuple, text_color: dict, bg_color: dict, font_size=10) -> None:
        x1, x2 = coords
        a1, b1 = x1
        a2, b2 = x2
        cell_range = f'{indexes_to_a1(a1, b1)}:{indexes_to_a1(a2, b2)}'
        time.sleep(1)
        worksheet.format(cell_range, self.get_paint_row_params(bg_color, text_color, font_size))

    def format_table(self, worksheet, size: tuple, write_result_point: tuple) -> None:
        text_color = {"red": 0, "green": 0, "blue": 0}
        headers_color = {"red": 0.99, "green": 0.89, "blue": 0.6}
        keywords_color = {"red": 0.43, "green": 0.62, "blue": 0.92}
        competitor_color = {"red": 0.64, "green": 0.75, "blue": 0.95}
        personal_color = {"red": 0.71, "green": 0.83, "blue": 0.65}
         
        write_result_row, write_result_col = write_result_point
        last_row, last_column = write_result_row + size[0] - 1, write_result_col + size[1] - 1

        counter = write_result_row + 2

        while counter < last_row:
            cell = counter, write_result_col
            self.format_worksheet(
                    worksheet,
                    (cell, cell),
                    text_color, keywords_color
            )
            counter += 3
            time.sleep(0.5)                   
    
        self.format_worksheet(
            worksheet,
            ((write_result_row, write_result_col + 1), (write_result_row, last_column)),
            text_color, headers_color, 14
        )
        
        time.sleep(1)      
        self.format_worksheet(
            worksheet,
            ((write_result_row + 1, write_result_col + 2), (last_row, last_column)),
            text_color, competitor_color
        )
        time.sleep(1)          

        middle_column = write_result_col + (last_column - write_result_col) // 2 + 1
        
        self.format_worksheet(
            worksheet,
            ((write_result_row + 1, write_result_col + 1), (last_row, write_result_col + 1)),
            text_color, personal_color
        )
        time.sleep(1)

        self.format_worksheet(
            worksheet,
            ((write_result_row + 1, middle_column), (last_row, middle_column)),
            text_color, personal_color
        )

        worksheet.merge_cells(f'{indexes_to_a1(write_result_row, write_result_col + 1)}:{indexes_to_a1(write_result_row, middle_column - 1)}')
        worksheet.merge_cells(f'{indexes_to_a1(write_result_row, middle_column)}:{indexes_to_a1(write_result_row, last_column)}')



    def _get_worksheet(self):
        service = gspread.service_account(filename=self.apikey_file_path)
        table = service.open_by_url(self.table)
        worksheet_names = [worksheet.title for worksheet in table.worksheets()]
        if self.product_name not in worksheet_names:
            table.add_worksheet(title=self.product_name, rows=1000, cols=1000)
        worksheet = [worksheet for worksheet in table.worksheets() if worksheet.title == self.product_name][0]

        return worksheet

    def write_statistic(self) -> None:
        worksheet = self._get_worksheet()

        statistic = self.monitoring_asins.format_statistic()
        statistic_size = len(statistic), len(statistic[0])
        write_result_point = self._get_write_cords(worksheet)
        last_cell = indexes_to_a1(write_result_point[0] + statistic_size[0], write_result_point[1] + statistic_size[1])
    
        values_update_diapason = f'{indexes_to_a1(*write_result_point)}:{last_cell}'
        worksheet.update(values_update_diapason, statistic, value_input_option='USER_ENTERED')

        self.format_table(worksheet, statistic_size, write_result_point)

    def _get_headers(self):
        return {
            'User-Agent': self.user_agents.get_random_user_agent(),
            'Cookie': self.cookie
        }

    def start_requests(self):
        asins = [self.personal_asin] + self.competitor_asins
        for asin in asins:
            url = self.get_item_link(asin)
            yield scrapy.Request(
                url, self.asins_scanner, headers=self._get_headers(), cb_kwargs={
                    'base_asin': asin,
                }
            )

    def asins_scanner(self, response, base_asin: str):
        asins = [base_asin]
        brand_href = response.css('#bylineInfo::attr(href)').get()
        if brand_href:
            brand_name = brand_href.split('/')[1]
            brand_name = brand_href.split('/')[2] if brand_name == 'stores' else brand_name
        else:
            brand_name = 'unknown'
        variations_body = response.css('ul.a-button-toggle-group')

        if variations_body:
            variations = variations_body.css('li::attr(data-defaultasin)').getall()
            variation_asins = [asin for asin in variations if asin]
            asins += variation_asins
        brand_name = f'{brand_name} ({base_asin})'
        self.monitoring_asins.append_asins(asins, brand_name)
        self.asins_counter -= 1
        self.monitoring_asins.create_statistic()

        if self.asins_counter == 0:
            self.monitoring_asins.sort_asins_data([self.personal_asin] + self.competitor_asins)
            self.monitoring_asins.create_statistic()

            for page_data in self.scan_pages_data:
                keyword, url = page_data
                time.sleep(5)
                yield scrapy.Request(
                    url=url, callback=self.monitoring_pages, headers=self._get_headers(), cb_kwargs={
                        'keyword': keyword,
                    }
                )

    @staticmethod
    def get_item_asin(item) -> str:
        return item.css('::attr(data-asin)').get()

    @staticmethod
    def item_is_advertising(item):
        return item.css('span.puis-label-popover-default')


    @staticmethod
    def get_sbv_asins(response) -> list:
        result = []
        sbv_body = response.css('[data-component-type="sbv-video-single-product"]')
        if sbv_body:
            sbv_data = sbv_body.css('div.a-size-small::attr(data-a-popover)').extract_first()
            if sbv_data:
                asin = re.compile(r'asin=(.*)&').findall(sbv_data)[0]
                result.append(asin)
        return result

    def get_sorted_main_asins(self, response) -> tuple:
        advertising_asins = []
        organic_asins = []

        page_asins = response.css('div.s-main-slot').css('::attr(data-asin)').getall()
        main_items = response.css('div.s-main-slot').css('div.s-asin')

        for item in main_items:
            item_asin = self.get_item_asin(item)
            if self.item_is_advertising(item):
                advertising_asins.append(item_asin)
            else:
                organic_asins.append(item_asin)

        sb_asins = list(set(page_asins) - set(advertising_asins + organic_asins))
        sbv_asins = self.get_sbv_asins(response)
        if sb_asins and not sb_asins[0]:
            sb_asins = sb_asins[1:]
        return organic_asins, advertising_asins, sb_asins, sbv_asins

    @staticmethod
    def check_occurrence(page_asins: list, asins: list) -> tuple:
        counter = 1
        for asin in page_asins:
            counter += 1
            if asin in asins:
                return counter, True
        return counter, False

    def scan_page(self, response, keyword: str) -> None:
        organic_asins, advertising_asins, sb_asins, sbv_asins = self.get_sorted_main_asins(response)
        for asins_data in self.monitoring_asins.asins:
            asins = asins_data['asins']
            brand_name = asins_data['brand_name']
            scan_data = list(
                map(
                    lambda page_asins: self.check_occurrence(page_asins, asins),
                    [organic_asins, advertising_asins, sb_asins, sbv_asins]
                )
            )

            self.monitoring_asins.append_statistic(keyword, brand_name, scan_data)

    @staticmethod
    def get_page_counter(response) -> int:
        counter = response.css('span.s-pagination-disabled::text').getall()[1]
        return int(counter)

    def monitoring_pages(self, response, keyword: str, page_index=1, counter=1):
        self.scan_page(response, keyword)
        if page_index == 1:
            self.pages_counter -= 1
            counter = self.get_page_counter(response)
        if page_index != counter:
            url = response.request.url
            page_index += 1
            # print(f'PAGE_INDEX: {page_index}')
            next_url = self.get_next_url(url, page_index)
            time.sleep(5)
            yield scrapy.Request(
                url=next_url, callback=self.monitoring_pages, headers=self._get_headers(), cb_kwargs={
                    'keyword': keyword,
                    'page_index': page_index,
                    'counter': counter
                }
            )
