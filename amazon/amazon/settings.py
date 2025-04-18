import django
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(".")))
# Do not forget the change iCrawler part based on your project name
os.environ["DJANGO_SETTINGS_MODULE"] = "webscraper.settings"

# This is required only if Django Version > 1.8

django.setup()
BOT_NAME = "amazon"

DOWNLOADER_MIDDLEWARES = {
    "rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
    "rotating_proxies.middlewares.BanDetectionMiddleware": 620,
}
SPIDER_MODULES = ["amazon.spiders"]
NEWSPIDER_MODULE = "amazon.spiders"

ROTATING_PROXY_CLOSE_SPIDER = False

# ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'

ROTATING_PROXY_LIST = [
    "http://bqdjoxpl:4fkosp25oquk@198.154.92.141:7916",
    "http://bqdjoxpl:4fkosp25oquk@198.154.92.205:7980",
    "http://bqdjoxpl:4fkosp25oquk@45.41.163.181:5224",
    "http://bqdjoxpl:4fkosp25oquk@185.216.104.170:7247",
    "http://bqdjoxpl:4fkosp25oquk@23.236.183.78:7850",
    "http://bqdjoxpl:4fkosp25oquk@104.253.84.88:7522",
    "http://bqdjoxpl:4fkosp25oquk@216.173.102.44:5082",
    "http://bqdjoxpl:4fkosp25oquk@45.38.116.253:8164",
    "http://bqdjoxpl:4fkosp25oquk@104.252.57.142:8064",
    "http://bqdjoxpl:4fkosp25oquk@212.42.192.16:5076",
    "http://bqdjoxpl:4fkosp25oquk@104.252.37.200:8124",
    "http://bqdjoxpl:4fkosp25oquk@107.175.57.39:9424",
    "http://bqdjoxpl:4fkosp25oquk@107.175.7.183:5058",
    "http://bqdjoxpl:4fkosp25oquk@185.216.104.144:7221",
    "http://bqdjoxpl:4fkosp25oquk@103.251.220.192:5263",
    "http://bqdjoxpl:4fkosp25oquk@198.46.180.113:7498",
    "http://bqdjoxpl:4fkosp25oquk@185.216.104.51:7128",
    "http://bqdjoxpl:4fkosp25oquk@198.46.181.66:6951",
    "http://bqdjoxpl:4fkosp25oquk@104.252.57.245:8167",
    "http://bqdjoxpl:4fkosp25oquk@104.252.37.223:8147",
]

# ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_BACKOFF_BASE = 60
ROTATING_PROXY_BACKOFF_CAP = 180
ROTATING_PROXY_PAGE_RETRY_TIMES = 2

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403, 302]
