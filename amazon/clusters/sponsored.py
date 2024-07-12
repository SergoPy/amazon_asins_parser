import gspread
import numpy

from datetime import datetime

import pandas

from webscraper.settings import MEDIA_ROOT


class CreateSponsoredTable:
    MAX_KEYWORD_LEN = 50
    COMPANY_BLACKLIST = ['Auto', 'NegativeExacts', 'NegativePATs', 'NegativePhrases', 'Broad']
    HEADERS = ['Product', 'Entity', 'Operation', 'Campaign Id', 'Draft Campaign Id', 'Portfolio Id', 'Ad Group Id',
               'Keyword Id', 'Product Targeting Id', 'Campaign Name', 'Start Date', 'End Date', 'State', 'Budget Type',
               'Budget', 'Bid Optimization', 'Bid Multiplier', 'Bid', 'Keyword Text', 'Match Type',
               'Product Targeting Expression', 'Ad Format', 'Landing Page URL', 'Landing Page Asins', 'Brand Entity Id',
               'Brand Name', 'Brand Logo Asset Id', 'Brand Logo URL', 'Creative Headline', 'Creative ASINs',
               'Video Media Ids', 'Creative Type']

    def __init__(self, table_link, bid_multiplier, type_, creative_asins='', brand_id='', brand_name='',
                 brand_logo='', headline='', video_ids=''):
        self.table_link = table_link
        self.type = type_
        self.google_sheet_table = self.google_sheet_connection()
        self.clusters_content, self.clusters_name = self.get_clusters_content()
        self.sponsored = self.get_bulk_name()
        self.bid_multiplier = self.get_bid_multiplier(bid_multiplier)
        self.negatives = self.get_negatives()
        self.creative_asins = creative_asins
        self.brand_id = brand_id
        self.brand_name = brand_name
        self.brand_logo = brand_logo
        self.headline = headline
        self.video_ids = video_ids
        self.result_data = []
        self.creative_type = self.get_creative_type()

    def get_creative_type(self):
        if self.type == 'Video':
            return 'video'
        return ''

    @staticmethod
    def get_bid_multiplier(multiplier: str) -> float:
        if not multiplier:
            return 1
        else:
            return 1 + float(multiplier) / 100

    @staticmethod
    def get_current_date():
        return datetime.today().strftime('%Y%m%d')

    def google_sheet_connection(self):
        connection = gspread.service_account(filename='clusters/apikey.json')
        return connection.open_by_url(self.table_link)

    def get_bulk_name(self):
        return self.clusters_name.replace('clusters', f'Sponsored{self.type}')

    @staticmethod
    def get_clusters_worksheet(worksheets):
        for worksheet in worksheets:
            if 'clusters' in worksheet.title.lower():
                return worksheet.title

    def get_negatives(self):
        negative_pats = self.clusters_content[-1][5:]
        return [f'asin="{negative}"' for negative in negative_pats if negative and len(negative) >= 10]

    def get_clusters_content(self):
        worksheets = self.google_sheet_table.worksheets()
        clusters_name = self.get_clusters_worksheet(worksheets)
        clusters = self.google_sheet_table.worksheet(clusters_name)
        return numpy.array(clusters.get_all_values()).T[2:], clusters_name

    def create_headers(self):
        self.result_data.append(self.HEADERS)

    def write_result(self):
        worksheets = [worksheet.title for worksheet in self.google_sheet_table.worksheets()]
        if self.sponsored not in worksheets:
            self.google_sheet_table.add_worksheet(self.sponsored, rows=10000, cols=35)
        self.google_sheet_table.values_update(
            self.sponsored,
            params={'valueInputOption': 'USER_ENTERED'},
            body={'values': self.result_data}
        )

    def get_campaign_id(self, header, count):
        if self.type == 'Video':
            table_type = self.type[0]
        else:
            table_type = ''
        name = header[1]
        if count:
            postfix = count + 1
        else:
            postfix = ''
        if 'exact' not in name.lower() and 'pat' not in name.lower() and 'brands' not in name.lower():
            return f'{header[1]}{postfix} [SB{table_type}] -SP'
        return f'{header[1]} - {header[2]}{postfix} [SB{table_type}] -SP'

    def get_bid(self, header):
        bid = header[4]
        if bid:
            return round(self.bid_multiplier * float(bid), 2)
        return ''

    def append_company_row(self, campaign, bid, keyword_body='', product='', type_='Keyword', match='exact'):
        self.result_data.append(['Sponsored Brands', type_, 'Create', campaign, '', '', '', '', '', '', '',
                                 '', 'Enabled', '', '', '', '', bid, keyword_body, match, product, '', '', '', '',
                                 '', '', '', '', '', ''])

    def append_company_header(self, campaign):
        creative = ''
        if self.type != 'Video':
            creative = self.creative_asins
        self.result_data.append(['Sponsored Brands', 'Campaign', 'Create', campaign, '', '', '', '', '', campaign,
                                 f'{self.get_current_date()}', '', 'Enabled', 'Daily', '300', 'manual', '-30', '',
                                 '', '', '', 'productCollection', '', creative, self.brand_id,
                                 self.brand_name, self.brand_logo, '', self.headline, self.creative_asins, self.video_ids,
                                 self.creative_type])

    def create_campaign(self, header, body, count):
        company_type = header[0]
        campaign = self.get_campaign_id(header, count)
        bid = self.get_bid(header)
        self.append_company_header(campaign)
        if company_type.lower() == 'pat':
            for keyword in body:
                if len(keyword) >= 10:
                    product = f'asin="{keyword}"'
                    self.append_company_row(campaign=campaign, bid=bid, product=product,
                                            match='', type_='Product targeting')
        elif company_type.lower() == 'category':
            for i, keyword in enumerate(body + self.negatives):
                if not i:
                    self.append_company_row(campaign=campaign, bid=bid, product=f'category="{keyword}"',
                                            type_='Product targeting', match='')
                else:
                    self.append_company_row(campaign=campaign, bid=bid, product=keyword,
                                            type_='Negative product targeting', match='')
        else:
            for keyword in body:
                self.append_company_row(campaign=campaign, bid=bid, keyword_body=keyword)

    def campaign_manager(self, header, body, count=0):
        body = [keyword for keyword in body if keyword and len(keyword) <= 50]
        if len(body):
            self.create_campaign(header, body[:300], count)
            return self.campaign_manager(header, body[300:], count + 1)

    def run(self):
        self.create_headers()
        for column in self.clusters_content:
            company_type = column[0].strip()
            if company_type and company_type not in self.COMPANY_BLACKLIST:
                headers = column[0:5]
                body = column[5:]
                self.campaign_manager(headers, body)
        self.write_result()

    def import_to_xlsx(self):
        filename = f'{self.sponsored}.xlsx'
        data = pandas.DataFrame(self.result_data)
        writer = pandas.ExcelWriter(f'{MEDIA_ROOT}{filename}', engine='xlsxwriter')
        data.to_excel(writer, sheet_name='welcome', index=False, header=False)
        writer.save()
        return filename


class CreateSponsoredDisplayTable:
    DEFAULT_COMPANY = {
            'views': {
                'types': ['category', 'similar', 'exact'],
                'times': [(7, 0.7), (14, 0.6), (30, 0.5), (60, 0.4), (90, 0.3)]
                },
            'purchases': {
                'types': ['category', 'related', 'exact'],
                'times': [(7, 0.8), (14, 0.7), (30, 0.6), (60, 0.5), (90, 0.4), (180, 0.3), (365, 0.2)]
                }
            }

    COMPANY = ['PAT', 'Category']
    HEADERS = ['Product', 'Entity', 'Operation', 'Campaign Id', 'Portfolio Id', 'Ad Group Id',
               'Ad Id', 'Targeting Id', 'Campaign Name', 'Ad Group Name', 'Start Date', 'End Date', 'State',
               'Tactic', 'Budget Type', 'Budget', 'SKU', 'Ad Group Default Bid', 'Bid', 'Bid Optimization',
               'Cost Type', 'Targeting Expression']

    def __init__(self, table_link: str, bid_optimization: str, vales: dict):
        self.table_link = table_link
        self.google_sheet_table = self.google_sheet_connection()
        self.clusters_content, self.clusters_name = self.get_clusters_content()
        self.sponsored, self.product_name = self.get_sponsored_name()
        self.negatives = self.get_negatives()
        self.bid_optimization = bid_optimization
        self.result_data = []
        self.cost_type = self.get_cost_type()
        self.created_company = []
        self.values = vales
        self.base_bid = float(self.values['tpa'])
        self.category_id = None
        self.base_scu = None

    def get_cost_type(self):
        if self.bid_optimization == 'Optimize for viewable impressions':
            return 'vCPM'
        return 'CPC'

    @staticmethod
    def get_current_date():
        return datetime.today().strftime('%Y%m%d')

    def google_sheet_connection(self):
        connection = gspread.service_account(filename='clusters/apikey.json')
        return connection.open_by_url(self.table_link)

    def get_sponsored_name(self):
        return self.clusters_name.replace('clusters', 'SponsoredDisplay'),\
               self.clusters_name.replace('(clusters)', '')

    @staticmethod
    def get_clusters_worksheet(worksheets):
        for worksheet in worksheets:
            if 'clusters' in worksheet.title.lower():
                return worksheet.title

    def get_negatives(self):
        negative_pats = self.clusters_content[-1][5:]
        return [f'asin="{negative}"' for negative in negative_pats if negative and len(negative) >= 10]

    def get_clusters_content(self):
        worksheets = self.google_sheet_table.worksheets()
        clusters_name = self.get_clusters_worksheet(worksheets)
        clusters = self.google_sheet_table.worksheet(clusters_name)
        return numpy.array(clusters.get_all_values()).T[2:], clusters_name

    def create_headers(self):
        self.result_data.append(self.HEADERS)

    def write_result(self):
        worksheets = [worksheet.title for worksheet in self.google_sheet_table.worksheets()]
        if self.sponsored not in worksheets:
            self.google_sheet_table.add_worksheet(self.sponsored, rows=10000, cols=35)
        self.google_sheet_table.values_update(
            self.sponsored,
            params={'valueInputOption': 'USER_ENTERED'},
            body={'values': self.result_data}
        )

    def get_campaign_data(self, header, count):
        name = f'{header[1]} [SD] -SP' #last fix
        if count:
            postfix = count + 1
        else:
            postfix = ''
        group_type = header[2]
        group = f'{header[2]}{postfix}'
        sku = header[3]
        bid = float(self.values[group_type.lower()])
        return name, group, sku, bid

    def append_campaign(self, campaign_id, number='T00020'):
        if campaign_id not in self.created_company:
            self.result_data.append([
                'Sponsored Display', 'Campaign', 'Create', campaign_id, '', '', '', '', campaign_id,
                '', self.get_current_date(), '', 'enabled', number, 'daily', '300', '', '', '', '', self.cost_type, ''
            ])
            self.created_company.append(campaign_id)

    def append_group(self, campaign_id, group, bid):
        self.result_data.append([
            'Sponsored Display', 'Ad group', 'Create', campaign_id, '', group, '', '', '',
            group, '', '', 'enabled', '', '', '', '', bid, '', self.bid_optimization, '', ''
        ])

    def append_item(self, type_, campaign_id, group, bid, item):
        self.result_data.append([
            'Sponsored Display', type_, 'Create', campaign_id, '', group, '', '', '',
            '', '', '', 'enabled', '', '', '', '', '', bid, '', '', item
        ])

    def append_product(self, campaign_id, sku, group):
        self.result_data.append([
            'Sponsored Display', 'Product ad', 'Create', campaign_id, '', group, '', '', '',
            '', '', '', 'enabled', '', '', '', sku, '', '', '', '', ''
        ])

    def create_campaign(self, header, body, count):
        company_type = header[0]
        name, group, sku, bid = self.get_campaign_data(header, count)
        self.base_scu = sku
        self.append_campaign(name)
        self.append_group(name, group, bid)
        self.append_product(name, sku, group)
        if company_type.lower() == 'pat':
            for keyword in body:
                if len(keyword) >= 10:
                    product = f'asin="{keyword}"'
                    self.append_item(type_='Contextual targeting', campaign_id=name,
                                     group=group, bid=bid, item=product)
        elif company_type.lower() == 'category':
            for i, keyword in enumerate(body + self.negatives):
                if not i:
                    product = f'category="{keyword}"'
                    self.category_id = product
                    self.append_item(type_='Contextual targeting', campaign_id=name,
                                     group=group, bid=bid, item=product)
                else:
                    self.append_item(type_='Negative product targeting', campaign_id=name,
                                     group=group, bid=bid, item=f'{keyword}')
        else:
            for keyword in body:
                self.append_item(type_='Negative product targeting', campaign_id=name,
                                 group=group, bid=bid, item=f'category="{keyword}"')

    def campaign_manager(self, header, body, count=0):
        body = [keyword for keyword in body if keyword]
        if len(body):
            self.create_campaign(header, body[:300], count)
            return self.campaign_manager(header, body[300:], count + 1)

    def create_default_campaign(self):
        for company in self.DEFAULT_COMPANY:
            data = self.DEFAULT_COMPANY[company]
            postfix = self.bid_optimization.split('for ')[1]
            for type_ in data['types']:
                campaign_id = f'{self.product_name}[SD] {type_} - {company} - {postfix} -SP'
                group = f'{type_} {company}'
                self.append_campaign(campaign_id, number='T00030')
                self.append_group(campaign_id, group, bid='')
                self.append_product(campaign_id, self.base_scu, group)
                for period in data['times']:
                    bid = period[1] * self.base_bid
                    if bid < 1 and self.cost_type == 'vCPM':
                        bid = 1

                    item = f'{company}=({type_}-product lookback={period[0]})'
                    if type_ == 'category':
                        item = f'{company}=({self.category_id} lookback={period[0]})'
                    self.append_item(type_='Audience targeting', campaign_id=campaign_id, group=group,
                                     bid=bid, item=item)

    def run(self):
        self.create_headers()
        for column in self.clusters_content:
            company_type = column[0].strip()
            if company_type and company_type in self.COMPANY:
                headers = column[0:5]
                body = column[5:]
                self.campaign_manager(headers, body)
        self.create_default_campaign()
        self.write_result()

    def import_to_xlsx(self):
        filename = f'{self.sponsored}.xlsx'
        data = pandas.DataFrame(self.result_data)
        writer = pandas.ExcelWriter(f'{MEDIA_ROOT}{filename}', engine='xlsxwriter')
        data.to_excel(writer, sheet_name='welcome', index=False, header=False)
        writer.save()
        return filename


def create_display(table: str, values: dict):
    bid_optimization = values['optimization_type']
    company = CreateSponsoredDisplayTable(table, bid_optimization, values)
    company.run()
    filename = company.import_to_xlsx()
    return filename


def create_sponsored(table: str, data: dict, video=False):
    brand_id = data['brand_entity_id']
    brand_name = data['brand_name']
    brand_logo = data.get('brand_logo_id', '')
    bid_multiplier = data['bids']
    video_ids = ''
    headline = ''
    if not video:
        type_ = 'Brands'
        creative_asins = data['creative_asins']
        headline = data['headline']
    else:
        type_ = 'Video'
        creative_asins = data['creative_asins_video']
        video_ids = data.get('media_ids', '')

    company = CreateSponsoredTable(table_link=table, type_=type_, bid_multiplier=bid_multiplier,
                                   creative_asins=creative_asins, brand_id=brand_id, brand_name=brand_name,
                                   brand_logo=brand_logo, headline=headline, video_ids=video_ids)
    company.run()
    filename = company.import_to_xlsx()
    return filename
