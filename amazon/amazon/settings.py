import django
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath('.')))
# Do not forget the change iCrawler part based on your project name
os.environ['DJANGO_SETTINGS_MODULE'] = 'webscraper.settings'

# This is required only if Django Version > 1.8

django.setup()
BOT_NAME = 'amazon'

DOWNLOADER_MIDDLEWARES = {
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}
SPIDER_MODULES = ['amazon.spiders']
NEWSPIDER_MODULE = 'amazon.spiders'

ROTATING_PROXY_CLOSE_SPIDER = False

# ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_LIST = [
    'http://user137997:yklevn@181.215.71.179:5516',
    'http://user137997:yklevn@181.215.71.173:5516',
    'http://user137997:yklevn@181.215.152.158:5516',
    'http://user137997:yklevn@77.83.195.232:5516',
    'http://user137997:yklevn@77.83.195.102:5516',
    'http://user137997:yklevn@77.83.195.37:5516',
    'http://user137997:yklevn@77.83.195.106:5516',
    'http://user137997:yklevn@77.83.195.71:5516',
    'http://user137997:yklevn@181.214.117.27:5516',
    'http://user137997:yklevn@181.215.71.138:5516',
    'http://user137997:yklevn@77.83.195.4:5516',
    'http://user137997:yklevn@77.83.195.112:5516',
    'http://user137997:yklevn@77.83.195.86:5516',
    'http://user137997:yklevn@77.83.195.174:5516',
    'http://user137997:yklevn@102.129.221.171:5516',
]
# ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_BACKOFF_BASE = 60
ROTATING_PROXY_BACKOFF_CAP = 180
ROTATING_PROXY_PAGE_RETRY_TIMES = 2

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403, 302]
