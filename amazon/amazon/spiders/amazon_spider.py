import json
import re
import gspread
import scrapy
from random_user_agent.params import HardwareType, SoftwareName, OperatingSystem
from random_user_agent.user_agent import UserAgent

from amazon.google_api import GoogleSheetsApi

from amazon.utils import indexes_to_a1


class AmazonSpider(scrapy.Spider):
    name = 'amazon'

    AMAZON_SEARCH_PATH = '/s?k='
    AMAZON_PRODUCT_PATH = '/dp/'
    INVALID_ITEM_URL = 'https://aax-us-iad.amazon.com'
    SP_DEF_COLUMN = 'Brand Defense'
    SP_ADV_COLUMN = 'Self Targeting'

    def __init__(self, urls, limit=1,
                 keywords=None, sp_def_asins='', sp_def_skus='', adv_variations_asins='', creterians="", table_link=None, apikey_file_path=None, cookie=None, **kwargs):
        super().__init__(self, **kwargs)

        self.urls = urls.split()
        self.limit = int(limit)
        self.cookie = cookie
        self.request_count = 0
        self.keywords = keywords.split()
        self.sp_def_asins = sp_def_asins.split()
        self.sp_def_skus = sp_def_skus.split()
        self.table_id = self.get_table_id(table_link)
        self.googlesheets_api = GoogleSheetsApi(
            self.table_id, apikey_file_path)
        self.creterians = json.loads(creterians)
        self.create_column_for_grouping()
        self.cords, self.write_data = self.get_categories_cords()
        self.user_agents = self.get_user_agents()
        self.base_url = self.get_base_url()
        self.sp_asins_counter = len(self.sp_def_asins)
        self.asins_cache = []
        self.sp_variations_asins = []
        self.adv_variations_asins = adv_variations_asins.split()

    def get_base_url(self) -> str:
        # print(f"base_url: {self.urls[0].split(self.AMAZON_SEARCH_PATH)[0]}")
        return self.urls[0].split(self.AMAZON_SEARCH_PATH)[0]

    @staticmethod
    def get_user_agents():
        user_agents = UserAgent(
            hardware_types=[HardwareType.COMPUTER.value],
            software_names=[SoftwareName.CHROME.value],
            operating_systems=[OperatingSystem.MACOS.value, OperatingSystem.LINUX.value,
                               OperatingSystem.MAC_OS_X.value],
            limit=100
        )
        return user_agents

    def create_column_for_grouping(self) -> None:
        category_mapping = {
            'reviews': 'TCA',
            'rating': 'LSA',
            'price': 'LPA'
        }
        subcategory_mapping = {
            'CA' : [["CA", "Photo", "Title", "Reviews", "Rating", "Price"]],
            'RA' : [["RA", "Photo", "Title", "Reviews", "Rating", "Price"]],
            'LSA' : ["Photo", "Rating", "Title", "Reviews", "Price"],
            'LPA' : ["Photo", "Price", "Title", "Reviews", "Rating"],
            'TCA' : ["Photo", "Reviews", "Title", "Rating", "Price"],
        }
        start_row, start_col = self.googlesheets_api.get_cord_by_name(
            "TPA")
        start_row = 1
        self.googlesheets_api.clear_from_column(start_col+1)

        needed_table_column_len = len(self.creterians) * 6 + 12 + 16
        self.googlesheets_api.ensure_columns(needed_table_column_len)

        current_col = start_col + 1
        diapason = f"{gspread.utils.rowcol_to_a1(start_row, current_col)}:{gspread.utils.rowcol_to_a1(start_row, current_col + 5)}"
        # diapason = f'{indexes_to_a1(start_row, current_col)}:' \
        #                        f'{indexes_to_a1(start_row, current_col + 5)}'
        current_col = current_col + 5
        self.googlesheets_api.update(
                    diapason, subcategory_mapping['CA'])

        for key in self.creterians:
            groups_list = []
            group_by_creterian_name = key.split("_")[0]
            group_by_creterian = key.split("_")[1].replace("-", "...")
            map_criterion_name = category_mapping[group_by_creterian_name]
            groups_list.append(f"{map_criterion_name} [{group_by_creterian}]")
            groups_list.extend(subcategory_mapping[map_criterion_name])
            print(f"groups_list: {groups_list}")
            current_col = current_col + 1
            # print(f"current_col: {current_col}")
            diapason = f"{gspread.utils.rowcol_to_a1(start_row, current_col)}:{gspread.utils.rowcol_to_a1(start_row, current_col+ 5)}"
            # print(f"diapason before: {diapason}")
            # diapason = f'{indexes_to_a1(start_row, current_col)}:' \
            #                    f'{indexes_to_a1(start_row, current_col + 5)}'
            # print(f"diapason after: {diapason}")
            current_col = current_col + 5
            self.googlesheets_api.update(
                    diapason, [groups_list])

        current_col = current_col + 1
        # diapason = f'{indexes_to_a1(start_row, current_col)}:' \
        #                        f'{indexes_to_a1(start_row, current_col + 5)}'
        diapason = f"{gspread.utils.rowcol_to_a1(start_row, current_col)}:{gspread.utils.rowcol_to_a1(start_row, current_col + 5)}"
        current_col = current_col + 5
        self.googlesheets_api.update(
                    diapason, subcategory_mapping['RA'])

    def format_url(self, url: str, search_number: int) -> str:
        split_url = url.split('page=')
        return f'{self.base_url}{split_url[0]}page={search_number}'

    @staticmethod
    def get_googlesheets_formula_photo(link: str) -> str:
        return f'=IMAGE("{link}")'

    @staticmethod
    def get_table_id(table_link) -> str:
        return table_link.split('/d/')[1].split('/')[0]

    def get_float_price(self, string_price: str):
        try:
            price = self._float(string_price.replace(',', '').strip('$£€'))
        except ValueError:
            price = None
        return price

    def get_categories_cords(self) -> tuple:
        print("in get categories_cord")
        cords = {}
        data = {}
        category_mapping = {
            'TCA': 'reviews',
            'LSA': 'rating',
            'LPA': 'price'
        }

        # print(f"self.creterians: {self.creterians}")

        for category in ['TCA', 'LSA', 'LPA', 'RA', 'CA', self.SP_DEF_COLUMN, self.SP_ADV_COLUMN]:
            cords[category.lower()] = self.googlesheets_api.get_cord_by_name(category)
            if category in category_mapping: #LPA
                print(f"category: {category}")
                # result = {'price_1-3': [1, 3],  'price_3-10': [3, 10], 'price_10-': [10, None],}
                key = category_mapping[category] # price
                for close_key in self.creterians:
                    category_key = close_key.split("_")[0] # price
                    # print(f"key: {key}; category_key: {category_key}")
                    if key == category_key:
                        group_by_creterian = close_key.split("_")[1].replace("-", "...")
                        cord_name = f"{category} [{group_by_creterian}]"
                        cords[cord_name.lower()] = self.googlesheets_api.get_cord_by_name(cord_name)
                        data[cord_name.lower()] = []
            data[category.lower()] = []
        print(f"cords: {cords}; data: {data}")
        return cords, data

    def save_product_data(self, asin: str, price: str, reviews: str, rating: str, title: str, photo_url: str) -> None:
        category, asin, oriented_value, value_1, value_2, value_3 = self.get_product_data(
            asin, price, reviews, rating, title)
        row, col = self.cords[category]
        # print(
        #     f"save_product_data category: {category}, row: {row}, col: {col}")
        photo = self.get_googlesheets_formula_photo(photo_url)
        self.write_data[category].append(
            [asin, photo, oriented_value, value_1, value_2, value_3])
        self.cords[category][0] += 1

    def write_product_data(self) -> None:
        print("in write_product_data")

        sp_def_key = self.SP_DEF_COLUMN.lower()
        sp_adv_key = self.SP_ADV_COLUMN.lower()

        sp_variations_asins_to_write = []
        for asin in set(self.sp_variations_asins):
            if asin in self.sp_def_asins:
                index = self.sp_def_asins.index(asin)
                # print(f"index: {index}")
                sku = self.sp_def_skus[index]
                formatted_value = f"{asin}|{sku}"
                sp_variations_asins_to_write.append([formatted_value])
            else:
                sp_variations_asins_to_write.append([asin])
        self.write_data[sp_def_key] = sp_variations_asins_to_write
        self.write_data[sp_adv_key] = [[asin]
                                       for asin in set(self.adv_variations_asins)]
        # print(f"self.write_data: {self.write_data}")
        for category in self.cords:
            print(f"in for: {category}")
            if self.write_data[category]:
                current_row = self.cords[category][0]
                current_col = self.cords[category][1]
                num_of_record = len(self.write_data[category])

                if category == sp_def_key:
                    diapason = f'{indexes_to_a1(current_row, current_col)}:' \
                               f'{indexes_to_a1(current_row + num_of_record, current_col)}'
                elif category == sp_adv_key:
                    diapason = f'{indexes_to_a1(current_row, current_col)}:' \
                               f'{indexes_to_a1(current_row + num_of_record, current_col)}'
                else:
                    diapason = f'{indexes_to_a1(current_row - num_of_record, current_col)}:' \
                               f'{indexes_to_a1(current_row, current_col + 5)}'
                # print(
                #     f"self.cords: {self.cords[category]},\n category: {category};\n diapason: {diapason};\n self.write_data: {self.write_data[category]};\n")
                self.googlesheets_api.update(
                    diapason, self.write_data[category])

    def title_contains_keywords(self, title: str) -> bool:
        title_words = re.findall(r'\b\w+\b', title.lower())
        for word in self.keywords:
            if word.lower() in title_words:
                return True
        return False

    @staticmethod
    def _float(string: str) -> float:
        return round(float(string), 2)

    def get_product_data(self, asin: str, price: str, reviews: str, rating: str, title: str) -> tuple:
        # print(
        #     f"asin: {asin}, price: {price}, reviews: {reviews}, rating: {rating}")
        category_mapping = {
            'reviews': 'TCA',
            'rating': 'LSA',
            'price': 'LPA'
        }
        if price:
            price_value = self.get_float_price(price)
        else:
            price_value = 'Not mentioned'

        if rating and rating != 'FREE' and "$" not in rating and rating != 'Currently':
            rating = rating
        else:
            rating = '0'

        if reviews and reviews != 'Or' and ',' in reviews and reviews != 'Only':
            reviews_count = int(reviews.replace(',', '')) if reviews else None
        else:
            reviews_count = '0'
        try:
            if self.keywords and title and self.title_contains_keywords(title):
                return 'ra', asin, title, reviews_count, self._float(rating), price_value
            
            for close_key in self.creterians:
                category_key = close_key.split("_")[0]
                if 'price' == category_key:
                    from_value, to_value = self.creterians[close_key]

                    map_criterion_name = category_mapping[category_key]
                    group_by_creterian = close_key.split("_")[1].replace("-", "...")
                    category_name = f"{map_criterion_name} [{group_by_creterian}]"

                    if (from_value is None or (price_value and price_value != 'Not mentioned' and price_value >= self._float(from_value))) and \
                            (to_value is None or (price_value and price_value != 'Not mentioned' and price_value <= self._float(to_value))):
                        # print(
                        #     f"from_value: {from_value}, to_value: {to_value}, price_value: {price_value}")
                        return category_name.lower(), asin, price_value, title, reviews_count, self._float(rating)
                    
            for close_key in self.creterians:
                category_key = close_key.split("_")[0]
                if 'reviews' == category_key:
                    from_value, to_value = self.creterians[close_key]

                    map_criterion_name = category_mapping[category_key]
                    group_by_creterian = close_key.split("_")[1].replace("-", "...")
                    category_name = f"{map_criterion_name} [{group_by_creterian}]"

                    reviews_count = int(reviews.replace(
                        ',', '')) if reviews else None

                    if (from_value is None or (reviews_count and reviews_count >= self._float(from_value))) and \
                            (to_value is None or (reviews_count and reviews_count <= self._float(to_value))):
                        # print(
                        #     f"from_value: {from_value}, to_value: {to_value}, reviews_count: {reviews_count}")
                        return category_name.lower(), asin, reviews_count, title, self._float(rating), price_value
            for close_key in self.creterians:
                category_key = close_key.split("_")[0]
                if 'rating' == category_key:
                    from_value, to_value = self.creterians[close_key]

                    map_criterion_name = category_mapping[category_key]
                    group_by_creterian = close_key.split("_")[1].replace("-", "...")
                    category_name = f"{map_criterion_name} [{group_by_creterian}]"

                    if (from_value is None or (rating and self._float(rating) >= self._float(from_value))) and \
                            (to_value is None or (rating and self._float(rating) <= self._float(to_value))):
                        # print(
                        #     f"from_value: {from_value}, to_value: {to_value}, rating: {rating}")
                        return category_name.lower(), asin, self._float(rating), title, reviews_count, price_value

        except ValueError:
            pass

        return 'ca', asin, title, reviews_count, self._float(rating), price_value

    def get_product_url(self, asin: str) -> str:
        return f'{self.base_url}{self.AMAZON_PRODUCT_PATH}{asin}'

    def start_requests(self):
        print(f"start_requests: {self.sp_def_asins}")
        if len(self.sp_def_asins):
            for asin in self.sp_def_asins:
                url = self.get_product_url(asin)
                yield scrapy.Request(url=url, callback=self.variation_scanner, headers={
                    'User-Agent': self.user_agents.get_random_user_agent(),
                    'Cookie': self.cookie
                }, cb_kwargs={
                    'base_asin': asin,
                })
        else:
            for url in self.urls:
                yield scrapy.Request(url=url, callback=self.scrape_pages, headers={
                    'User-Agent': self.user_agents.get_random_user_agent(),
                    'Cookie': self.cookie
                })

    def variation_scanner(self, response, base_asin):
        asins = [base_asin]
        variations_body = response.css('ul.a-button-toggle-group')
        if variations_body:
            # print(f"variations_body: {variations_body}")
            variations = variations_body.css(
                'li::attr(data-defaultasin)').getall()
            print(f"variation_asins: {variations}")
            variation_asins = [asin for asin in variations if asin]
            asins += variation_asins
        self.asins_cache += asins
        self.sp_variations_asins += asins
        self.sp_asins_counter -= 1
        if self.sp_asins_counter == 0:
            for url in self.urls:
                yield scrapy.Request(url=url, callback=self.scrape_pages, headers={
                    'User-Agent': self.user_agents.get_random_user_agent(),
                    'Cookie': self.cookie
                })

    def scrape_pages(self, response):
        current_page = response.request.url
        next_page = response.css(
            'div.s-pagination-container').css('a::attr(href)').get()
        search_pages = [current_page]
        if self.limit > 1 and next_page:
            for i in range(2, self.limit + 1):
                search_pages.append(self.format_url(next_page, i))

        for page in search_pages:
            yield scrapy.Request(page, dont_filter=True, callback=self.scrape, headers={
                'User-Agent': self.user_agents.get_random_user_agent(),
                'Cookie': self.cookie
            }, meta={'dont_merge_cookies': True})
            self.request_count += 1


    def scrape_item(self, item, search_tag, retry_count=0):
        asin = item.css('::attr(data-asin)').get()
        if asin and asin not in self.asins_cache and len(asin) >= 10:
            photo_url = item.css(
                'div.sg-col-inner').css('div.s-image-square-aspect').css('img::attr(src)').get()
            item_data = item.css('div.sg-col-inner').css(f'div.{search_tag}')
            title = item_data.css('h2.a-size-mini').css('span::text').get()
            price = item_data.css(
                'span.a-price').css('span.a-offscreen::text').get()
            review_data = item_data.css('span::attr(aria-label)').getall()
            if review_data:
                try:
                    rating, reviews = review_data[0].split()[
                        0], review_data[1].split()[0]
                    # print(f"rating and review in try: {rating} {reviews}")
                except IndexError:
                    try:
                        rating = review_data[0].split()[0]
                    except IndexError:
                        rating = None
                    reviews = None
                    # print(f"rating and review in except: {rating} {reviews}")

            else:
                rating, reviews = None, None
            if not retry_count and not item_data:
                # print(f"asin: {asin} not in item_data: item_data: {item_data}; retry_count: {retry_count}, title: {title}; price: {price}, rating: {rating}, reviews: {reviews}, item: {item}")
                self.scrape_item(item, 'a-spacing-small', retry_count=1)
            else:
                # print(f"asin: {asin} in item_data: item_data: {item_data}; retry_count: {retry_count}, title: {title}; price: {price}, rating: {rating}, reviews: {reviews}")
                self.save_product_data(
                    asin, price, reviews, rating, title, photo_url)
                self.asins_cache.append(asin)

    def scrape_page(self, item_list):
        for item in item_list:
            self.scrape_item(item, 'puis-padding-left-small', 0)

    def scrape(self, response):

        main_items = response.css('div.s-main-slot').css('div.s-asin')

        advertising_items = []
        advertising_body = response.css(
            '.sg-col-12-of-16 .s-widget-spacing-large')
        for adv_sector in advertising_body:
            standard_items = adv_sector.css('.a-carousel-card')
            if standard_items:
                for item in standard_items:
                    advertising_items.append(item)

        self.scrape_page(advertising_items + main_items)
        self.request_count -= 1
        if self.request_count == 0:
            print("in scrape")
            self.write_product_data()
