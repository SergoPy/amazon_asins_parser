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
    "http://bqdjoxpl:4fkosp25oquk@45.41.169.210:6871",
    "http://bqdjoxpl:4fkosp25oquk@104.239.105.132:6662",
    "http://bqdjoxpl:4fkosp25oquk@45.41.173.156:6523",
    "http://bqdjoxpl:4fkosp25oquk@104.168.25.160:5842",
    "http://bqdjoxpl:4fkosp25oquk@38.170.190.64:9415",
    "http://bqdjoxpl:4fkosp25oquk@104.168.8.216:5669",
    "http://bqdjoxpl:4fkosp25oquk@45.61.97.141:6667",
    "http://bqdjoxpl:4fkosp25oquk@206.206.64.211:6172",
    "http://bqdjoxpl:4fkosp25oquk@89.249.192.179:6578",
    "http://bqdjoxpl:4fkosp25oquk@92.113.231.113:7198",
    "http://bqdjoxpl:4fkosp25oquk@23.27.78.144:5724",
    "http://bqdjoxpl:4fkosp25oquk@89.249.192.220:6619",
    "http://bqdjoxpl:4fkosp25oquk@154.30.244.113:9554",
    "http://bqdjoxpl:4fkosp25oquk@38.170.172.240:5241",
    "http://bqdjoxpl:4fkosp25oquk@67.227.37.31:5573",
    "http://bqdjoxpl:4fkosp25oquk@45.61.96.105:6085",
    "http://bqdjoxpl:4fkosp25oquk@107.172.116.54:5510",
    "http://bqdjoxpl:4fkosp25oquk@167.160.180.201:6752",
    "http://bqdjoxpl:4fkosp25oquk@89.249.198.155:6241",
    "http://bqdjoxpl:4fkosp25oquk@23.27.75.40:6120",
    "http://bqdjoxpl:4fkosp25oquk@161.123.115.191:5212",
    "http://bqdjoxpl:4fkosp25oquk@216.173.84.40:5955",
    "http://bqdjoxpl:4fkosp25oquk@192.186.172.55:9055",
    "http://bqdjoxpl:4fkosp25oquk@45.249.59.241:6217",
    "http://bqdjoxpl:4fkosp25oquk@216.74.115.62:6656",
    "http://bqdjoxpl:4fkosp25oquk@142.147.240.195:6717",
    "http://bqdjoxpl:4fkosp25oquk@89.249.194.219:6618",
    "http://bqdjoxpl:4fkosp25oquk@198.46.137.105:6309",
    "http://bqdjoxpl:4fkosp25oquk@192.177.87.196:6042",
    "http://bqdjoxpl:4fkosp25oquk@23.26.94.154:6136",
    "http://bqdjoxpl:4fkosp25oquk@192.186.172.188:9188",
    "http://bqdjoxpl:4fkosp25oquk@173.214.177.164:5855",
    "http://bqdjoxpl:4fkosp25oquk@67.227.42.23:6000",
    "http://bqdjoxpl:4fkosp25oquk@38.154.217.170:7361",
    "http://bqdjoxpl:4fkosp25oquk@50.114.15.206:6191",
    "http://bqdjoxpl:4fkosp25oquk@50.114.15.76:6061",
    "http://bqdjoxpl:4fkosp25oquk@107.173.93.148:6102",
    "http://bqdjoxpl:4fkosp25oquk@198.23.128.138:5766",
    "http://bqdjoxpl:4fkosp25oquk@193.36.172.138:6221",
    "http://bqdjoxpl:4fkosp25oquk@67.227.1.240:6521",
    "http://bqdjoxpl:4fkosp25oquk@173.211.69.169:6762",
    "http://bqdjoxpl:4fkosp25oquk@23.26.71.163:5646",
    "http://bqdjoxpl:4fkosp25oquk@107.172.116.35:5491",
    "http://bqdjoxpl:4fkosp25oquk@185.216.107.222:5799",
    "http://bqdjoxpl:4fkosp25oquk@45.61.97.29:6555",
    "http://bqdjoxpl:4fkosp25oquk@23.26.94.72:6054",
    "http://bqdjoxpl:4fkosp25oquk@198.37.98.150:5680",
    "http://bqdjoxpl:4fkosp25oquk@45.41.169.24:6685",
    "http://bqdjoxpl:4fkosp25oquk@69.58.12.57:8062",
    "http://bqdjoxpl:4fkosp25oquk@173.214.177.243:5934",
    "http://bqdjoxpl:4fkosp25oquk@192.186.185.226:6785",
    "http://bqdjoxpl:4fkosp25oquk@179.61.166.190:6613",
    "http://bqdjoxpl:4fkosp25oquk@23.27.93.103:5682",
    "http://bqdjoxpl:4fkosp25oquk@179.61.245.51:6830",
    "http://bqdjoxpl:4fkosp25oquk@104.168.8.73:5526",
    "http://bqdjoxpl:4fkosp25oquk@198.12.112.19:5030",
    "http://bqdjoxpl:4fkosp25oquk@50.114.98.96:5580",
    "http://bqdjoxpl:4fkosp25oquk@161.123.101.154:6780",
    "http://bqdjoxpl:4fkosp25oquk@166.88.58.81:5806",
    "http://bqdjoxpl:4fkosp25oquk@193.36.172.166:6249",
    "http://bqdjoxpl:4fkosp25oquk@23.95.244.252:6205",
    "http://bqdjoxpl:4fkosp25oquk@192.186.185.198:6757",
    "http://bqdjoxpl:4fkosp25oquk@23.26.94.160:6142",
    "http://bqdjoxpl:4fkosp25oquk@38.170.189.194:9760",
    "http://bqdjoxpl:4fkosp25oquk@166.88.48.5:5331",
    "http://bqdjoxpl:4fkosp25oquk@107.174.136.196:6138",
    "http://bqdjoxpl:4fkosp25oquk@173.211.69.241:6834",
    "http://bqdjoxpl:4fkosp25oquk@23.94.138.230:6504",
    "http://bqdjoxpl:4fkosp25oquk@45.56.175.229:5903",
    "http://bqdjoxpl:4fkosp25oquk@23.26.94.17:5999",
    "http://bqdjoxpl:4fkosp25oquk@38.170.172.60:5061",
    "http://bqdjoxpl:4fkosp25oquk@104.239.124.175:6453",
    "http://bqdjoxpl:4fkosp25oquk@23.236.170.168:9201",
    "http://bqdjoxpl:4fkosp25oquk@23.27.91.212:6291",
    "http://bqdjoxpl:4fkosp25oquk@38.170.169.21:5262",
    "http://bqdjoxpl:4fkosp25oquk@149.57.17.186:5654",
    "http://bqdjoxpl:4fkosp25oquk@198.12.112.235:5246",
    "http://bqdjoxpl:4fkosp25oquk@166.88.238.81:6061",
    "http://bqdjoxpl:4fkosp25oquk@66.78.32.34:5084",
    "http://bqdjoxpl:4fkosp25oquk@89.249.198.183:6269",
    "http://bqdjoxpl:4fkosp25oquk@136.0.109.135:6421",
    "http://bqdjoxpl:4fkosp25oquk@174.140.200.65:6345",
    "http://bqdjoxpl:4fkosp25oquk@192.177.87.241:6087",
    "http://bqdjoxpl:4fkosp25oquk@67.227.113.44:5584",
    "http://bqdjoxpl:4fkosp25oquk@142.147.245.195:5886",
    "http://bqdjoxpl:4fkosp25oquk@45.41.178.133:6354",
    "http://bqdjoxpl:4fkosp25oquk@142.147.245.96:5787",
    "http://bqdjoxpl:4fkosp25oquk@185.216.105.195:6772",
    "http://bqdjoxpl:4fkosp25oquk@146.103.44.122:6674",
    "http://bqdjoxpl:4fkosp25oquk@45.61.97.190:6716",
    "http://bqdjoxpl:4fkosp25oquk@142.111.245.6:5873",
    "http://bqdjoxpl:4fkosp25oquk@198.46.241.157:6692",
    "http://bqdjoxpl:4fkosp25oquk@166.88.245.132:5477",
    "http://bqdjoxpl:4fkosp25oquk@198.46.241.67:6602",
    "http://bqdjoxpl:4fkosp25oquk@45.41.173.100:6467",
    "http://bqdjoxpl:4fkosp25oquk@45.61.100.17:6285",
    "http://bqdjoxpl:4fkosp25oquk@92.113.1.178:5878",
    "http://bqdjoxpl:4fkosp25oquk@216.74.114.31:6314",
    "http://bqdjoxpl:4fkosp25oquk@216.74.118.84:6239",
    "http://bqdjoxpl:4fkosp25oquk@45.61.121.18:6617",
]
# ROTATING_PROXY_LIST_PATH = '../proxies/proxies.txt'
ROTATING_PROXY_BACKOFF_BASE = 60
ROTATING_PROXY_BACKOFF_CAP = 180
ROTATING_PROXY_PAGE_RETRY_TIMES = 2

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403, 302]
