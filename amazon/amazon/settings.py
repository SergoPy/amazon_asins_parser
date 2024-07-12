import os
import sys

sys.path.append(os.path.dirname(os.path.abspath('.')))
# Do not forget the change iCrawler part based on your project name
os.environ['DJANGO_SETTINGS_MODULE'] = 'webscraper.settings'

# This is required only if Django Version > 1.8
import django

django.setup()
BOT_NAME = 'amazon'

DOWNLOADER_MIDDLEWARES = {
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}
SPIDER_MODULES = ['amazon.spiders']
NEWSPIDER_MODULE = 'amazon.spiders'

ROTATING_PROXY_CLOSE_SPIDER = False

#ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_LIST = [
    'http://user137997:yklevn@23.26.126.22:5948',
    'http://user137997:yklevn@102.129.151.13:5948',
    'http://user137997:yklevn@166.0.173.231:5948',
    'http://user137997:yklevn@104.193.227.74:5948',
    'http://user137997:yklevn@23.26.126.157:5948',
    'http://user137997:yklevn@154.16.242.204:5948',
    'http://user137997:yklevn@166.0.173.75:5948',
    'http://user137997:yklevn@166.0.173.77:5948',
    'http://user137997:yklevn@166.0.173.144:5948',
    'http://user137997:yklevn@23.26.126.35:5948',
    'http://user137997:yklevn@102.129.221.150:5948',
    'http://user137997:yklevn@166.0.173.228:5948',
    'http://user137997:yklevn@102.129.221.158:5948',
    'http://user137997:yklevn@154.16.242.5:5948',
    'http://user137997:yklevn@108.165.197.228:5948',
]
#ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_BACKOFF_BASE = 60
ROTATING_PROXY_BACKOFF_CAP = 180
ROTATING_PROXY_PAGE_RETRY_TIMES = 2

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403, 302]
