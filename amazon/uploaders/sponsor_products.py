import random
import re
import time

import gspread
import numpy
import pyotp
from random_user_agent.params import HardwareType, SoftwareName, OperatingSystem, Popularity
from random_user_agent.user_agent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

from .settings import ACCOUNTS_AUTH_TOKENS, BUDGET, MIN_WAIT, MAX_WAIT, ROTATING_PROXY_LIST_PATH


class SponsorBrandsUploader:
    CAMPAIGNS = ['SEED', 'STR Low', 'Launched', 'Exact', 'Exact TOP', 'Broad', 'Exact LOW', 'Brands', 'Variations']
    NAME = 'SB'
    NEGATIVE_CAMPAIGNS = ['NegativeExacts', 'NegativePhrases']

    @staticmethod
    def get_sb_amazon_domain(base_url: str) -> str:
        return re.compile(r'https://www.(.*)/').findall(base_url)[0]

    def __init__(self, login: str, password: str, headline: str, creative_asins: str, brand_name: str, logo: str,
                 media: str, media_sbv: str, bid_mode: str, apikey_filepath: str, table_link: str, base_domain: str,
                 entity_id=''):
        sb_base_domain = self.get_sb_amazon_domain(base_domain)

        self.login = login
        self.password = password
        self.auth_secret_code = self._get_auth_secret_code(login)
        self.headline = headline
        self.brand_name = brand_name
        self.creative_asins = creative_asins
        self.bid_mode = float(bid_mode)
        self.logo = logo
        self.media = media
        self.media_sbv = media_sbv
        self.auth_base_url = f'https://advertising.{sb_base_domain}/cb'
        self.auth_url = self._get_auth_url(entity_id)
        self.totp = self._get_totp_handler()
        self.google_sheet_table = self._google_sheet_connection(apikey_filepath, table_link)
        self.campaigns_counter = self._get_campaign_counter()
        self.campaign_creation_url = None
        self.negatives = {key: [] for key in self.NEGATIVE_CAMPAIGNS}

    def __enter__(self):
        self.driver = self._get_driver()
        return self

    @staticmethod
    def _get_auth_secret_code(email: str) -> str:
        return ACCOUNTS_AUTH_TOKENS[email]

    def _get_auth_url(self, entity_id: str) -> str:
        return f'{self.auth_base_url}?entityId={entity_id}' if entity_id else self.auth_base_url

    def _get_totp_handler(self):
        return pyotp.TOTP(self.auth_secret_code)

    def get_current_auth_code(self) -> str:
        return self.totp.now()

    def _get_driver(self):
        options = Options()
        options.headless = True
        options.set_preference("general.useragent.override", self._get_user_agent())
        service = Service(GeckoDriverManager().install())
        web_driver = webdriver.Firefox(options=options, service=service)
        web_driver.set_window_position(0, 0)
        web_driver.set_window_size(1920, 1080)
        return web_driver

    @staticmethod
    def _google_sheet_connection(apikey_filepath: str, table_link):
        connection = gspread.service_account(filename=apikey_filepath)
        return connection.open_by_url(table_link)

    @staticmethod
    def _get_clusters_worksheet(worksheets) -> str:
        for worksheet in worksheets:
            if 'clusters' in worksheet.title.lower():
                return worksheet.title

    def _get_clusters_content(self):
        worksheets = self.google_sheet_table.worksheets()
        clusters_name = self._get_clusters_worksheet(worksheets)
        clusters = self.google_sheet_table.worksheet(clusters_name)
        return numpy.array(clusters.get_all_values()).T[2:]

    def _get_campaign_counter(self) -> dict:
        return {campaign_name: 0 for campaign_name in self.CAMPAIGNS}

    @staticmethod
    def _get_proxy():
        proxy = Proxy()
        with open(ROTATING_PROXY_LIST_PATH, 'r', encoding='utf8') as f:
            proxy_list = [line.strip() for line in f if line.strip()]
            random_proxy = random.choice(proxy_list)
            proxy.proxy_type = ProxyType.MANUAL
            proxy.http_proxy = random_proxy
            proxy.ssl_proxy = random_proxy
            return proxy

    @staticmethod
    def _get_user_agent():
        popularity = [Popularity.POPULAR.value]
        software_names = [SoftwareName.FIREFOX.value]
        operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.MACOS.value,
                             OperatingSystem.LINUX.value]

        hardware_types = [HardwareType.COMPUTER.value]

        user_agent = UserAgent(popularity=popularity, software_names=software_names,
                               operating_systems=operating_systems, hardware_types=hardware_types,
                               limit=100).get_random_user_agent()

        return user_agent

    def _webdriver_waiter(self, expected_condition):
        return WebDriverWait(self.driver, MAX_WAIT).until(expected_condition)

    @staticmethod
    def _insert_value(elem, value: str) -> None:
        for char in value:
            timeout_random = random.randint(10, 30)
            elem.send_keys(char)
            time.sleep(timeout_random / 100)

    def _sign_in(self):
        print(self.auth_url)
        self.driver.get(self.auth_url)
        print(self.driver.current_url)

        email = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'email')))
        password = self.driver.find_element(By.NAME, 'password')
        self._insert_value(email, self.login)
        self._insert_value(password, self.password)

        submit_button = self.driver.find_element(By.ID, 'signInSubmit')
        submit_button.click()

        otp_code = self.get_current_auth_code()
        otp = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'otpCode')))
        self._insert_value(otp, otp_code)
        sign_in_button = self.driver.find_element(By.ID, 'auth-signin-button')
        sign_in_button.click()

    def _double_wait_until_condition_met(self, expected_condition):
        try:
            element = self._webdriver_waiter(expected_condition)
        except WebDriverException:
            element = self._webdriver_waiter(expected_condition)

        return element

    def _switch_to_create_campaign(self):
        if self.campaign_creation_url:
            self.driver.get(self.campaign_creation_url)
        else:
            self.campaign_creation_url = self.driver.current_url



    def _choose_campaign_type(self):
        sb_button = self._webdriver_waiter(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, '[data-e2e-id="sspa_cb_ingress_button_continue_hsa"]')
            )
        )
        sb_button.click()

    def _switch_to_append_campaign(self):
        self._switch_to_create_campaign()
        self._choose_campaign_type()

    @staticmethod
    def _clear_input(elem):
        elem.send_keys(Keys.CONTROL + 'a')
        elem.send_keys(Keys.BACKSPACE)

    def _append_campaign_header(self, values: dict):
        campaign_name_input = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'campaignName')))
        self._clear_input(campaign_name_input)
        self._insert_value(campaign_name_input, values['campaign_name'])


        budget_input = self.driver.find_element(By.CSS_SELECTOR, '#budget-field-wrapper-id > fieldset > div > span:nth-child(2) > div > div:nth-child(2) > div.campaign-budget-input > div.sc-storm-ui-20034903__sc-1sj9x5i-3.fzwEGu.sc-fzoNJl.kUMlmY > div > input')
        self._insert_value(budget_input, BUDGET)

        ad_group_name_input = self.driver.find_element(By.NAME, 'adGroupName')
        self._clear_input(ad_group_name_input)
        ad_group_name_input.send_keys(values['ad_group_name'])

    def _append_campaign_products(self):
        insert_asins_button = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="ups_asins_list_tab"]'))
        )
        insert_asins_button.click()

        asins_field = self._webdriver_waiter(
            EC.presence_of_element_located((By.ID, 'ucb:sb:ucb-sb-ups:ups-product-list-input'))
        )
        asins_field.send_keys(self.creative_asins)

        add_button = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e-id="ups-add-product-list"]')
        add_button.click()

    def _bid_settings(self, bid: str, campaign_type: str):
        bid_ = float(bid) * self.bid_mode / 100 + float(bid)
        str_bid = str(round(bid_, 2))
        bid_dropdown = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="kwp-bid-selector-dropdown"]'))
        )
        bid_dropdown.click()

        bid_mode_button = self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[value="CUSTOM"]')))
        bid_mode_button.click()

        bid_field = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e-id="kwp-bid-selector-input-field"]')
        self._insert_value(bid_field, str_bid)

        phrase_checkbox = self.driver.find_element(By.ID, 'ucb:sb:ucb-sb-kwp:kwp-match-type-phrase')
        phrase_checkbox.click()

        if campaign_type == 'Broad':
            exact_checkbox = self.driver.find_element(By.ID, 'ucb:sb:ucb-sb-kwp:kwp-match-type-exact')
            exact_checkbox.click()
        else:
            broad_checkbox = self.driver.find_element(By.ID, 'ucb:sb:ucb-sb-kwp:kwp-match-type-broad')
            broad_checkbox.click()

    def _fill_negative_input(self, negatives, negatives_input) -> None:
        for i in range(len(negatives) // 500):
            negatives_to_insert = '\r\n'.join(negatives[500 * i:500 * (i + 1)])
            negatives_input.send_keys(negatives_to_insert)
            add_button = self._webdriver_waiter(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-takt-id="kwp-enter-list-add-keywords-to-editor-button"]')
            )).find_element(By.TAG_NAME, 'button')
            add_button.click()

    def _append_negatives_broad_campaign(self) -> None:
        negatives_input = self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '[id="ucb:sb:ucb-sb-negative-kwp:kwp-enter-list-text-input-area"]')
        ))

        negative_phrases = self.negatives['NegativePhrases']
        negative_exact = self.negatives['NegativeExacts']

        self._fill_negative_input(negative_exact, negatives_input)
        switch_negative_mode_button = self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#negativeKeywords-field-wrapper-id > fieldset > div > span:nth-child(2) > div > div > div:nth-child(1) > div:nth-child(1) > div > fieldset > div > div > label:nth-child(2)')
        ))

        switch_negative_mode_button.click()

        self._fill_negative_input(negative_phrases, negatives_input)

    def _append_campaign_keywords(self, values: dict):
        enter_list_button = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="kwp-enter-list-tab"]')))
        enter_list_button.click()

        keywords_field = self._webdriver_waiter(
            EC.presence_of_element_located((By.ID, 'ucb:sb:ucb-sb-kwp:kwp-enter-list-text-input-area'))
        )
        self._bid_settings(values['bid'], values['campaign_type'])
        keywords = values['keywords']

        if values['campaign_type'] == 'Broad':
            keywords.replace(' ', '+')
            self._append_negatives_broad_campaign()
        keywords_field.send_keys(keywords)

        add_button = self._webdriver_waiter(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-e2e-id="kwp-enter-list-add-keywords-to-editor-button"]')
            )
        )
        add_button.click()
        if values['campaign_type'] == 'Broad':
            self._append_negatives_broad_campaign()

    def _switch_to_main_creative(self, retry=0):
        time.sleep(10)
        try:
            done_button = self._webdriver_waiter(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-takt-id="ahsoka_back_button"]'))
            )
            done_button.click()
        except WebDriverException:
            if not retry:
                retry += 1
                self._switch_to_main_creative(retry)

    def _upload_logo(self):
        upload_logo_button = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="brand-logo-panel-link"]'))
        )
        upload_logo_button.click()

        try:
            update_logo = self._webdriver_waiter(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-takt-id="ahsoka_edit_img_panel_expander"]'))
            )
            update_logo.click()
        except WebDriverException:
            pass

        field = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-takt-id="ahsoka_featured_img_upload_button"]')))
        field.send_keys(self.logo)
        self._switch_to_main_creative()

    def _upload_media(self):
        upload_image_button = self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '[data-e2e-id="custom-image-panel-link"]')
        ))
        upload_image_button.click()

        upload_file_field = self._webdriver_waiter(
            EC.presence_of_element_located((By.ID, 'ahsoka_custom_img_add_image_menu_file_input'))
        )
        upload_file_field.send_keys(self.media)
        self._switch_to_main_creative()

    def _append_media(self):
        self._upload_logo()
        self._upload_media()

    def _append_brand_name_field(self):
        brand_name_button = self._webdriver_waiter((
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="sponsor-panel-link"]'))
        ))
        brand_name_button.click()
        brand_name_field = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-takt-id="ahsoka_brand_name_input"]'))
        )
        self._clear_input(brand_name_field)
        self._insert_value(brand_name_field, self.brand_name)
        self._switch_to_main_creative()

    def _append_ad_group_field(self, ad_name: str):
        ad_name_field = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'adName')))
        self._clear_input(ad_name_field)
        self._insert_value(ad_name_field, ad_name)

    def _append_headline_field(self):
        headline_button = self._webdriver_waiter(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[data-e2e-id="headline-panel-link"]'))
        )
        headline_button.click()
        headline_field = self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '[data-takt-id="ahsoka_headline_input"]'))
        )
        headline_field.send_keys(self.headline)
        self._switch_to_main_creative()

    def _append_creative(self, ad_name: str):
        self._append_ad_group_field(ad_name)
        self._append_brand_name_field()
        self._append_media()
        self._append_headline_field()

    def _select_creative_mode(self):
        # not used for SB parsing
        pass

    def _finish_create(self) -> None:
        time.sleep(6)  # to avoid automatic hoisting to the top by amazon
        submit_button = self._webdriver_waiter(EC.element_to_be_clickable((By.ID, 'sspa_hsa_createCampaign')))
        submit_button.click()

    def _create_campaign(self, values: dict):
        self._append_campaign_header(values)
        self._select_creative_mode()

        select_new_page_button = self.driver.find_element(By.ID, 'landing-page-radio-group-productList')
        select_new_page_button.click()

        self._append_campaign_products()
        self._append_campaign_keywords(values)
        self._append_creative(values['ad_name'])

        self._finish_create()

    def _create_group(self, values: dict):
        ad_group = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'adGroupName')))
        self._clear_input(ad_group)
        self._insert_value(ad_group, values['ad_group_name'])

        self._append_campaign_keywords(values)
        self._append_headline_field()

        self._finish_create()

    def _switch_to_append_group(self):
        ad_group_button = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="navigation-create-ad-group-link"]')))
        ad_group_button.click()

    @staticmethod
    def _get_keywords(fields: list[str]) -> str:
        return '\r\n'.join([field for field in fields if field])

    def _get_campaign_name(self, campaign_name: str) -> str:
        return f'{campaign_name} [{self.NAME}] -SP'

    def _get_campaign_values(self, campaign) -> dict:
        campaign_name_raw = campaign[1]
        campaign_name_parts = campaign_name_raw.split('(')
        ad_name = campaign_name_parts[0].strip()
        campaign_type = campaign_name_parts[1].split(')')[0]
        campaign_name = self._get_campaign_name(campaign_name_raw)
        keywords = self._get_keywords(campaign[5:])

        return {
            'campaign_name': campaign_name,
            'ad_group_name': campaign[2],
            'ad_name': ad_name,
            'scu': campaign[3],
            'bid': campaign[4],
            'campaign_type': campaign_type,
            'keywords': keywords,
        }

    def _campaign_is_exist(self) -> bool:
        try:
            campaign_name_settings_body = WebDriverWait(self.driver, MIN_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     '[data-takt-id="sspa_sp_settings_campaignName"]')
                )
            )
            WebDriverWait(campaign_name_settings_body, MIN_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[style="vertical-align: inherit;"]')
                )
            )
            return True

        except WebDriverException:
            return False

    def _create_campaign_or_ad_group(self, campaign, retry=True):
        values = self._get_campaign_values(campaign)
        campaign_type = values['campaign_type']
        try:
            if self.campaigns_counter[campaign_type] == 0:
                self._switch_to_append_campaign()
                self._create_campaign(values)
            else:
                self._switch_to_append_group()
                self._create_group(values)
            self.campaigns_counter[campaign_type] += 1
            print(self.driver.current_url)
        except KeyError:
            if retry and not self._campaign_is_exist():
                self._create_campaign_or_ad_group(campaign, False)

    def _append_negatives(self, campaign) -> None:
        negatives = [field for field in campaign[5:] if field]
        self.negatives[campaign[0]] += negatives

    def _create_campaigns(self, clusters_data):
        for campaign in clusters_data:
            campaign_name = campaign[0]
            keywords = campaign[5]
            if campaign_name in self.CAMPAIGNS and keywords:
                self._create_campaign_or_ad_group(campaign)
            elif campaign_name in self.NEGATIVE_CAMPAIGNS and keywords:
                self._append_negatives(campaign)

    def run(self):
        clusters_data = self._get_clusters_content()
        self._sign_in()
        self._create_campaigns(clusters_data)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()


class SponsorBrandVideoUploader(SponsorBrandsUploader):
    UPLOAD_VIDEO_TIMEOUT = 600
    NAME = 'SBV'

    def _wait_until_video_uploaded(self):
        WebDriverWait(self.driver, self.UPLOAD_VIDEO_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 '[id="ahsoka-video-upload-success-message"]')
            )
        )

    def _append_media(self):
        upload_video_button = self.driver.find_element(
            By.CSS_SELECTOR, '[data-e2e-id="video-panel-link"]'
        )

        upload_video_button.click()
        self._webdriver_waiter(EC.presence_of_element_located((By.ID, 'ahsoka-video-upload-menu-trigger'))).click()
        upload_video_field = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-takt-id="ahsoka_video_upload_button"]'))
        )
        upload_video_field.send_keys(self.media_sbv)
        self._wait_until_video_uploaded()

        self._switch_to_main_creative()

    def _append_creative(self, ad_name: str):
        self._append_ad_group_field(ad_name)
        self._append_media()

    def __select_products_search_mode(self):
        self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-takt-id="ups_listpage_brand_selector"]'))
        ).click()

        self._webdriver_waiter(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, '[data-e2e-id="ups-brand-select-ups_search_all_amazon_dropdown_label"]'
            ))
        ).click()

    def _append_campaign_products(self):
        self.__select_products_search_mode()
        products_input = self._webdriver_waiter(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="ups-asin-search-input"]'))
        )
        sbv_creative_asin = self.creative_asins.split(',')[0].strip()
        products_input.send_keys(sbv_creative_asin)

        search_button = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e-id="ups-candidate-search-btn"]')
        search_button.click()

        try:
            self._webdriver_waiter(
                EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e-id="ups-asin-{sbv_creative_asin}"]'))
            )
            add_product_button = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e-id="asin-item-add-button"]')
            add_product_button.click()
        except TimeoutException:
            self._append_campaign_products()

    def _select_creative_mode(self):
        video_mode_button = self.driver.find_element(By.CSS_SELECTOR,
                                                     '[data-takt-id="sspa-ucb-hsa-adformat-video"]')
        video_mode_button.click()

    def _create_group(self, values: dict):
        ad_group = self._webdriver_waiter(EC.presence_of_element_located((By.NAME, 'adGroupName')))
        self._clear_input(ad_group)
        self._insert_value(ad_group, values['ad_group_name'])

        self._select_creative_mode()
        self._append_campaign_products()
        self._append_campaign_keywords(values)
        self._append_creative(values['ad_name'])

        self._finish_create()


def run_amazon_media_uploader(values: dict, upload_mode: str) -> None:
    uploaders = {
        'SB': SponsorBrandsUploader,
        'SBV': SponsorBrandVideoUploader
    }

    uploaders_names = upload_mode.split(' and ')

    for uploader_name in uploaders_names:
        uploader_class = uploaders.get(uploader_name)
        with uploader_class(**values) as uploader:
            uploader.run()
