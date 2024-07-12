import datetime
import csv
import random
import re
import time
import os
from pathlib import Path

import pyotp
from random_user_agent.params import HardwareType, SoftwareName, OperatingSystem, Popularity
from random_user_agent.user_agent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException

from amazon.models import AdvertisingMonitoring
from .settings import ACCOUNTS_AUTH_TOKENS, MAX_WAIT, ROTATING_PROXY_LIST_PATH


class UploadException(Exception):
    pass


class AdvertisingScanner:
    ADVERTISING_INDICATORS_SETTING_CSS = [
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-impressions-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-clicks-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-ctr-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-spend-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-cpc-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-orders-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-sales-check-box"]',
        '[id="UCM-CM-APP:ALL_PORTFOLIOS:column-manager-acos-check-box"]'
    ]
    ADVERTISING_STATS_PARAMS = [
        '[data-e2e-id="kpiElement_ads_att_sales"]',
        '[data-e2e-id="kpiElement_impressions"]',
        '[data-e2e-id="kpiElement_acos"]',
        '[data-e2e-id="kpiElement_ctr"]',
        '[data-e2e-id="kpiElement_ad_spend"]'
    ]
    REQUIRED_METRIC = ['ACOS', 'CTR', 'CPC', 'Orders', 'Impressions', 'Sales', 'Spend']
    MEDIA_ROOT = os.path.join(Path(__file__).resolve().parent.parent, 'media/')

    @staticmethod
    def get_sb_amazon_domain(base_url: str) -> str:
        return re.compile(r'https://www.(.*)/').findall(base_url)[0]

    def __init__(self,
                 adv_monitoring_data,
                 login: str,
                 product_name: str,
                 account_name: str,
                 start_date: str,
                 end_date: str,
                 password: str,
                 base_url: str,
                 target_acos: str,
                 entity_id: str):

        sb_base_domain = self.get_sb_amazon_domain(base_url)
        self.account_name = account_name
        self.product_name = product_name
        self.start_date, self.end_date = start_date, end_date
        self.adv_monitoring_data = adv_monitoring_data
        self.login = login
        self.password = password
        self.auth_secret_code = self._get_auth_secret_code(login)
        self.auth_base_url = f'https://sellercentral.{sb_base_domain}'
        self.totp = self._get_totp_handler()
        self.inventory_url = self.auth_base_url + '/inventory'

        self.business_report = f'{self.auth_base_url}/business-reports/ref=xx_sitemetric_dnav_xx#/report?'
        self.business_report_by_parent_item = f'{self.business_report}id=102%3ADetailSalesTrafficByParentItem'
        self.business_report_by_child_item = f'{self.business_report}id=102%3ADetailSalesTrafficByChildItem'

        self.seller_central_url = f'https://advertising.{sb_base_domain}/cm/campaigns?entityId={entity_id}'
        self.get_not_variational_asin_data_url = f'https://sellercentral.amazon.com/business-reports/' \
                                                 f'ref=xx_sitemetric_dnav_xx#/report?id=102%3ADetailSalesTrafficBy' \
                                                 f'ParentItem&chartCols=&columns=0%2F1%2F2%2F7%2F8%2F13%2F14%2F19%2' \
                                                 f'F20%2F25%2F26%2F27%2F28%2F29%2F30%2F31%2F32%2F33%2F34%2F35%2F36' \
                                                 f'{self._get_date_query_param(self.start_date, self.end_date)}'
        self.get_variational_asin_data_url = f'https://sellercentral.amazon.com/business-reports/' \
                                             f'ref=xx_sitemetric_dnav_xx#/report?id=102%3ADetailSalesTrafficByChild' \
                                             f'Item&chartCols=&columns=0%2F1%2F2%2F3%2F8%2F9%2F14%2F15%2F20%2F21%2F26' \
                                             f'%2F27%2F28%2F29%2F30%2F31%2F32%2F33%2F34%2F35%2F36%2F37' \
                                             f'{self._get_date_query_param(self.start_date, self.end_date)}&sortCol=' \
                                             f'SC_MA_ChildASIN_25991&sortOrder=asc'
        self._random_account_name = None

    def __enter__(self):
        self.driver = self._get_driver()
        return self

    @staticmethod
    def _get_auth_secret_code(email: str) -> str:
        return ACCOUNTS_AUTH_TOKENS[email]

    def _get_totp_handler(self):
        return pyotp.TOTP(self.auth_secret_code)

    def get_current_auth_code(self) -> str:
        return self.totp.now()

    def _get_driver(self):
        options = Options()
        options.headless = True
        options.add_argument("--headless")
        options.set_preference("general.useragent.override", self._get_user_agent())
        service = Service(GeckoDriverManager().install())
        # web_driver = webdriver.Firefox(service=service, options=options)

        # install_dir = "/snap/firefox/current/usr/lib/firefox"
        # driver_loc = os.path.join(install_dir, "geckodriver")
        # binary_loc = os.path.join(install_dir, "firefox")

        # service = Service(driver_loc)
        # options = webdriver.FirefoxOptions()
        # options.binary_location = binary_loc
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", f"{self.MEDIA_ROOT}")
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        web_driver = webdriver.Firefox(service=service, options=options)
        web_driver.set_window_position(0, 0)
        web_driver.set_window_size(1920, 1080)
        return web_driver

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
    def _clear_input(elem):
        elem.send_keys(Keys.CONTROL + 'a')
        elem.send_keys(Keys.BACKSPACE)

    @staticmethod
    def _insert_value(elem, value: str) -> None:
        for char in value:
            timeout_random = random.randint(10, 30)
            elem.send_keys(char)
            time.sleep(timeout_random / 100)

    def _pick_checkbox_if_not_picked(self, css_selector: str) -> None:
        checkbox = self._double_wait_until_condition_met(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        if not checkbox.is_selected():
            checkbox.click()
        timeout = random.randint(2, 5) / 10
        time.sleep(timeout)

    def _sign_in(self, url):
        self.driver.get(url)
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


    def _double_wait_until_condition_met(self, expected_condition): # function for find element with retry
        try:
            element = self._webdriver_waiter(expected_condition)
        except WebDriverException:
            element = self._webdriver_waiter(expected_condition)

        return element

    def _amazon_adv_select_campaign(self):
        try:
            campaign_input = self._webdriver_waiter(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[id="UCM-CM-APP:ALL_PORTFOLIOS:searchInput"]')
                ))
            self._clear_input(campaign_input)


        except WebDriverException:
            close_popup_btn = self._webdriver_waiter(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Dismiss Alert"]')
                )
            )
            close_popup_btn.click()

        finally:
            campaign_input = self.driver.find_element(By.CSS_SELECTOR, '[id="UCM-CM-APP:ALL_PORTFOLIOS:searchInput"]')
            self._clear_input(campaign_input)
            time.sleep(1)

            campaign_input.send_keys(self.product_name)
            campaign_input.send_keys(Keys.ENTER)

            columns_btn = self._double_wait_until_condition_met(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="picker"]')))

            columns_btn.click()

    def _switch_to_seller_portfolios(self):
        try:
            portfolios_btn = self._webdriver_waiter(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-eventid="portfolios"]')
            ))
            portfolios_btn.click()

        except WebDriverException:
            close_popup_btn = self._webdriver_waiter(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Dismiss Alert"]')
                )
            )
            close_popup_btn.click()
        finally:
            portfolios_btn = self.driver.find_element(By.CSS_SELECTOR, '[data-eventid="portfolios"]')
            portfolios_btn.click()

    def _amazon_adv_campaigns_settings(self):
        self._amazon_adv_select_campaign()
        custom_columns_btn = self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR,
            '[data-e2e-id="customizeButton"]')
        ))
        custom_columns_btn.click()

        for checkbox in self.ADVERTISING_INDICATORS_SETTING_CSS:
            self._pick_checkbox_if_not_picked(checkbox)

        apply_btn = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e-id="saveButton"]')
        apply_btn.click()

    @staticmethod
    def _get_str_time(date):
        date_list = list(map(lambda x: int(x), date.split('/')))
        date_list.reverse()
        date_list[1], date_list[2] = date_list[2], date_list[1]
        day = datetime.datetime(*date_list)
        day_ = day.strftime(f'%A, %B %d, 20%y').replace(' 0', ' ')
        return day_

    def _click_calendar_day(self, str_date, is_start_date=True):
        status = 'start' if is_start_date else 'end'
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, f'[aria-label="Choose {str_date} as your {status} date."]'
            ).click()
        except WebDriverException:
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         f'[aria-label="Selected as {status} date. {str_date}"]')
            except WebDriverException as exc:
                status = 'end' if is_start_date else 'start'
                self.driver.find_element(By.CSS_SELECTOR,
                                         f'[aria-label="Selected as {status} date. {str_date}"]').click()


    def _save_portfolios_report(self):
        self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e-id="export"]'))).click()
        time.sleep(6)

    def set_up_calendar_date(self):

        self._webdriver_waiter(EC.presence_of_element_located(
            (By.CSS_SELECTOR,
            '[data-e2e-id="dateRangePickerButton"]'))
        ).click()

        start_str_date = self._get_str_time(self.start_date)
        end_str_date = self._get_str_time(self.end_date)

        self._click_calendar_day(start_str_date, is_start_date=True)
        self._click_calendar_day(end_str_date, is_start_date=False)
        self.driver.find_element(By.XPATH,
                                 '/html/body/div[1]/div[2]/div[2]/div/div/div/div/div[2]/div[2]/button[2]').click()

    def _scrape_portfolios_data(self):
        today = datetime.datetime.now()
        month = today.strftime('%B')[:3]
        str_date = today.strftime(f'{month}_%d_20%y').replace('_0', '_')
        portfolios_report_filename = f'Portfolios_{str_date}.csv'
        portfolios_report_file_path = self.MEDIA_ROOT + portfolios_report_filename
        with open(portfolios_report_file_path) as report:
            report_reader = csv.DictReader(report)
            for campaign in report_reader:
                for metric in campaign:
                    campaign_name = campaign['Portfolio']
                    value = campaign[metric]
                    metric = metric.split('(')[0]
                    if metric in self.REQUIRED_METRIC:
                        self.adv_monitoring_data.append_metric(campaign_name, metric, value)
            os.remove(portfolios_report_file_path)

    def scan_advertisement_stats(self):
        self.driver.get(self.seller_central_url)

        self._switch_to_seller_portfolios()
        self._amazon_adv_campaigns_settings()
        self.set_up_calendar_date()
        self._save_portfolios_report()
        self._scrape_portfolios_data()

    @staticmethod
    def _swap_day_to_month(date):
        date_list = list(map(lambda x: int(x), date.split('-')))
        date_list[0], date_list[1] = date_list[1], date_list[0]
        return '/'.join(map(lambda x: str(x), date_list))

    def _scan_business_report(self):
        for asin in self.adv_monitoring_data.adv_monitoring_data:
            if asin.is_variational:
                report_url = self.business_report_by_child_item
            else:
                report_url = self.business_report_by_parent_item
            report_url += self._get_date_query_param(self.start_date, self.end_date)
            if self.driver.current_url != report_url:
                self.driver.get(report_url)


    @staticmethod
    def _get_date_query_param(start_date: str, end_date: str) -> str:
        start_date_list = start_date.split('/')
        start_date_list.reverse()
        start_date_list[1], start_date_list[2] = start_date_list[2], start_date_list[1]
        end_date_list = end_date.split('/')
        end_date_list.reverse()
        end_date_list[1], end_date_list[2] = end_date_list[2], end_date_list[1]
        return f'&fromDate={"-".join(start_date_list)}&toDate={"-".join(end_date_list)}'

    def _choose_sellercentral_account(self):
        time.sleep(3)
        self._webdriver_waiter(EC.presence_of_element_located((By.CLASS_NAME, 'partner-dropdown-button'))).click()
        self._webdriver_waiter(EC.presence_of_element_located((By.CLASS_NAME, 'partner-level')))
        companies = self.driver.find_elements(By.CLASS_NAME, 'partner-level')
        account_name = self.account_name.split(' (')[0]
        for company in companies:
            if company.text == self._random_account_name:
                company.find_element(By.CLASS_NAME, 'dropdown-arrow').click()
                break
        for company in companies:
            if company.text == account_name:
                try:
                    company_name  = re.findall(r'\((.*?)\)', self.account_name)[-1]
                    company.click()
                    time.sleep(5)
                    countries = company.find_elements(By.TAG_NAME, 'li')
                    for country in countries:
                        if country.text == company_name:
                            country.click()
                            break
                except WebDriverException:
                    pass
                break

    def _get_item_inventory_report(self, asin):
        asin_input = self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[id="myitable-search"]')))
        self._insert_value(asin_input, asin)
        time.sleep(0.5)
        asin_input.send_keys(Keys.ENTER)
        # self._webdriver_waiter(
        #     EC.presence_of_element_located(
        #         (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[2]/div[5]/div/table/tbody/tr[2]/td[9]/div/div[1]/span/a')
        #     )
        # )
        try:
            self._webdriver_waiter(
                EC.presence_of_element_located((By.CLASS_NAME, 'mt-variation-icon mt-variation-expand'))).click()
            self._webdriver_waiter(EC.presence_of_element_located((By.CLASS_NAME, 'mt-row mt-variations-row-child')))
            self.driver.find_elements(By.CLASS_NAME, 'mt-row mt-variations-row-child')
            print(1)
            products_quantity = list(self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[2]/div[5]/div/table/tbody/tr[2]/td[9]/div/div[1]/span/a').text)
        except WebDriverException:
            products_quantity = []
            self.driver.find_element(By.CSS_SELECTOR, '[data-action="myitable-fetch-rows"]').click()
            self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-column="asin"]')))
            time.sleep(3)
            variatonal_asins = self.driver.find_elements(By.CSS_SELECTOR, '[data-column="asin"]')
            print(2)
            print(variatonal_asins)

            for e in variatonal_asins:
                print(e.text)
            time.sleep(8765856)
                # try:
                #     quantity_input = e.find_element(By.CLASS_NAME, 'a-input-text main-entry mt-input-text')
                #     quantity_value = quantity_input.get_attribute('value')
                #     print('quantity value:' + quantity_value)
                #
                # except WebDriverException:
                #     quantity = e.find_element(By.CLASS_NAME, 'a-popover-trigger a-declarative').text
                #     print('quantity:' + quantity)
                # for asins_data_object in self.adv_monitoring_data.asins_data:
                #     asins = asins_data_object.asins
                #     print(asins)
                #     if e.text in asins:
                #         try:
                #             quantity_input = e.find_element(By.CLASS_NAME, 'a-input-text main-entry mt-input-text')
                #             quantity_value = quantity_input.get_attribute('value')
                #             print('quantity value:' + quantity_value)
                #
                #             products_quantity.append(quantity_value)
                #         except WebDriverException:
                #             quantity = e.find_element(By.CLASS_NAME, 'a-popover-trigger a-declarative').text
                #             print('quantity:' + quantity)
                #             products_quantity.append(quantity)
        print(products_quantity)
        time.sleep(976789)
        return products_quantity

    def _get_inventory_report(self):
        self.driver.get(self.inventory_url)
        for asin_data in self.adv_monitoring_data.asins_data:
            parent_asin = asin_data.asins[0]
            quantity = self._get_item_inventory_report(parent_asin)
            asin_data.append_stock_data(quantity)

    def _collect_stock_info(self):
        self._choose_sellercentral_account()
        self._get_inventory_report()

    def get_not_variational_asin_data(self):
        self.driver.get(self.get_not_variational_asin_data_url)
        self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[label="Download (.csv)"]'))).click()
        time.sleep(5)

    @staticmethod
    def _get_business_report_by_item(asins: list, report_reader, key) -> list:
        for item_data in report_reader:

            if item_data[key] in asins:

                return     [
                                item_data[r'Unit Session Percentage'],
                                item_data[r'Ordered Product Sales'],
                                item_data[r'Ordered Product Sales - B2B'],
                                item_data[r'Sessions - Total'],
                                item_data[r'Sessions - Total - B2B']
                            ]

        return []

    def _collect_business_report_info(self):
        today = datetime.datetime.now()
        date = f'-{today.strftime("%m-%d-%y")}'.replace('-0', '-', 1)
        report_filename = f'BusinessReport{date}.csv'
        child_report_filepath = self.MEDIA_ROOT + report_filename
        parent_report_filepath = self.MEDIA_ROOT + report_filename.replace('.', '(1).')

        with open(child_report_filepath) as child_report, open(parent_report_filepath) as parent_report:
            parent_report_reader = csv.DictReader(parent_report)
            child_report_reader = csv.DictReader(child_report)
            for asin_data in self.adv_monitoring_data.asins_data:
                asins = asin_data.asins
                if not asin_data.is_variational:
                    key = '(Child) ASIN'
                    business_report_data = self._get_business_report_by_item(asins, child_report_reader, key)
                else:
                    key = r'\ufeff(Parent) ASIN'
                    business_report_data = self._get_business_report_by_item(asins, parent_report_reader, key)

                if len(business_report_data):
                    asin_data.append_business_report_data(*business_report_data)
        os.remove(child_report_filepath)
        os.remove(parent_report_filepath)

    def get_variational_asin_data(self):
        self._log_in_random_account()
        self._choose_sellercentral_account()
        self.driver.get(self.get_variational_asin_data_url)
        self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[label="Download (.csv)"]'))).click()
        time.sleep(5)

    def _choose_random_account(self, accounts: list):
        choice = random.choice(accounts)
        if choice.text:
            try:
                choice.find_element(By.CLASS_NAME, 'picker-spinner-container')
                self._choose_random_account(accounts)
            except NoSuchElementException:
                try:
                    choice.find_element(By.CLASS_NAME, 'picker-spinner')
                    self._choose_random_account(accounts)
                except WebDriverException:
                    return choice

    def _log_in_random_account(self):
        self.driver.get(self.inventory_url)
        self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-v-3f8abec6=""]')))
        picker_columns = self.driver.find_elements(By.CSS_SELECTOR,  '[data-v-0909db80=""]')
        random_account = self._choose_random_account(
            picker_columns[0].find_elements(By.CSS_SELECTOR, '[data-v-3f8abec6=""]'))
        while not random_account:
            try:
                random_account = self._choose_random_account(
                    picker_columns[0].find_elements(By.CSS_SELECTOR, '[data-v-3f8abec6=""]'))
            except WebDriverException:
                pass
        random_account_name = random_account.text
        random_account.click()
        time.sleep(5)
        self._webdriver_waiter(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-v-3f8abec6=""]')))
        for e in self.driver.find_elements(By.CSS_SELECTOR,  '[data-v-0909db80=""]'):
            if e not in picker_columns:
                picker_columns.append(e)
        countries = picker_columns[-1].find_elements(By.CSS_SELECTOR, '[data-v-3f8abec6=""]')
        time.sleep(6)
        random_country = self._choose_random_account(countries)
        while not random_country:
            try:
                random_country = self._choose_random_account(countries)
            except WebDriverException:
                pass
        random_country.click()


        select_account_btn = self._webdriver_waiter(
            EC.presence_of_element_located((By.CLASS_NAME, 'picker-switch-accounts-button')))
        select_account_btn.click()
        try:
            self._webdriver_waiter(EC.presence_of_element_located((By.CLASS_NAME, 'partner-dropdown')))
        except WebDriverException:
            self._log_in_random_account()
        finally:
            self._random_account_name = random_account_name




    def run(self):
        self._sign_in(self.inventory_url)
        self.get_variational_asin_data()
        self.get_not_variational_asin_data()
        self._choose_sellercentral_account()
        self._collect_business_report_info()
        # self._collect_stock_info()
        self.scan_advertisement_stats()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()


# advertising_monitoring = AdvertisingMonitoring()
# advertising_monitoring.append_asin_data(['B08337MD2T'], 'Cap', '5')
# with AdvertisingScanner(advertising_monitoring, login='nicholas@scalingpeak.com', password='deathr0w',
#                         base_url='https://www.amazon.com/', target_acos='',
#                         entity_id='ENTITY2CFQNIT9EBPHE',
#                         product_name='Jojoba Oil', start_date='02/04/2023',
#                         end_date='03/02/2023', account_name='GreenBeautyInc (United States)') as scanner:
#     scanner.run()
