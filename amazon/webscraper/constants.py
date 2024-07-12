AMAZON_DOMAIN = 'www.amazon.com'
COUNTRY_URLS = {'US': 'https://www.amazon.com/',
                'CA': 'https://www.amazon.ca/',
                'UK': 'https://www.amazon.co.uk/',
                'DE': 'https://www.amazon.de/',
                'FR': 'https://www.amazon.fr/',
                'ES': 'https://www.amazon.es/',
                'IT': 'https://www.amazon.it/',
                }

COUNTRY_COOKIES = {
    'US': 'ubid-main=135-0952764-6651357; session-id=141-3828063-2737951; session-id-apay=141-3828063-'
          '2737951; session-id-time=2082787201l; i18n-prefs=USD; lc-main=en_US; session-token=easp6TMUD'
          '67TuFObnGtOJq5pEEQMrMr3/eNogPVr0nyrA2vnadYwa46F56KCyPEY+e857lDNmb+1oP5flqmOJ9j0l82UfXrwAH4DmJ'
          'okuHRW30vuH53z9fncr/83dWLJkvCJWhKj1pDcMa4cnvP+WcbVNCiouEfulICg4h6k+Xc4XGOoM4+VkoeqSfANlAu3Ii7'
          'HFgBBwY1OD3X5u3e5eZgzlCyhyoFH',
    'CA': 'session-id=139-5885032-8204726; session-id-time=2082787201l; i18n-prefs=CAD; ubid-acbca=135-'
          '8423491-6481749; session-token=MfvjsedqXDdwCNiP1dLO/PUwEIQsGc6l5GWHjR2ZJKXT5o/K5ZI1WvqcaKjmOni'
          'bJ743f8zpkRxFXPszwyj9vX7OsBk8TEv4CU9e/YU3mEw3+w91egXmpK7ZHS4/4LtBwF1sbM8RDuroqAi0aJ15O/sJdimJU'
          '0C+fzZYsDptrqkjsrIxFyN7B3lKHvvnf3rl1TUV8VDobaO5PaKzZE/3hV5qLmviLYeK; csm-hit=tb:WCW7JHTCGNG0Z0'
          'KV4G0A+b-WCW7JHTCGNG0Z0KV4G0A|1665967698779&t:1665967698779&adb:adblk_no',
    'UK': 'session-id=258-6371230-7642260; i18n-prefs=GBP; ubid-acbuk=262-5217066-7931245; lc-acbuk=en_GB;'
          ' session-token="rRO6kjDEH3MAKywOKg17inEwgL+cJ6RJjMvznwzYTLeu951GKk1Y/UItp0fMqlxF2Z+P3qCRl3dN1FIr/'
          'tYJkRNsU3vXIU/MS5l48nXgC+IGU4xEoKhrTRKgwBcltiwcQ4x0+Iif+tsT8uXhdOXXSda1ZtkgtFJ46jd6USMF4qsUysu3ij'
          '6DZCSKrnGFyJeQ5ia0mxkfX2+ufbwzuBKlg2pV9p9VjWxchJpHFypkUYM="; session-id-time=2082787201l',
    'DE': 'session-id=262-6287114-7711863; i18n-prefs=EUR; lc-acbde=en_GB; ubid-acbde=259-2381984-3585034; '
          'session-token=qN0k9kTGzwv5asbfZRhIUH8yi9x0roY6iHhPbf9MK94uawbJhMJHJ6KsqDygFdYaQn8rYVx/T2Vh+9vAsT'
          '5EKFtBxaGAh/gzerRXS+fi7k8QzT+JYStWWGuhZCH38/d+7P7r6Zs1f3DP4G9b/RQpEuDT435qworu2wqFCySuum6DEgINGUMP/'
          'PlL01bMeEF/wL2NwJG6k8WNzsFEIinjaVV8RaxdVqE7; session-id-time=2082787201l',
    'FR': 'session-id=262-6282254-4197055; i18n-prefs=EUR; ubid-acbfr=257-6627018-0203041; session-token=s/BixeK'
          '29w1yp3numv4O1aOAlAeQOSO5e2icnVSNJUka7PNFcjMa4WoTpULD2ncKaCLiFcb/WkMAc2RQPh08294ceqGEhnPCs0Oj95X6hs/'
          'fFJPKZi3+pRc5AmmzUvpOYNWQ7ee1KZIdaHoBWZgcvszwsqB+LxyfcipP6RIhJK5OEe0ayHWBYr+fgtXVewezkkbUkuuOEicO6BoY'
          'xs4LbDNNEtxilpux; session-id-time=2082787201l',
    'ES': 'session-id=257-2338414-2040949; i18n-prefs=EUR; ubid-acbes=258-9771405-2008759; session-token=SqLw7jU'
          'EpcZhw4fA0a66cXqhGVUa6+9mZimcAmcCmQGYF+lUd+iOah7mXa5EITB3yGfABnRkiALbHE71XE/9EoTKRqHSzl2aEa233wa6HR5'
          'CAwpDuCxfylVIj3m6aFQl09vZmZjWEn5VCZUJi5JMOB68NBf55OwI43TwEMtQMY7B2cS9PjCTRdB+8eP3o4owc+J1L8w0UGG7BbcH'
          '1MQhr2/D1rv7Xddk; session-id-time=2082758401l',
    'IT': 'session-id=260-0301589-2403037; i18n-prefs=EUR; ubid-acbit=258-7225020-9425310; session-token="AsT4VCA9'
          'DdM7bjX45zLAnicGEdXx3lo+v04QMRUqbiGVS3eB+r6KxR3jnMH8LFq4qc6kkqmKqSWPE/wMMrzHd9akD7wnp1cXkbku/mekefVrVn'
          'HUAhSEvinB57cEWBK6eYzzzLhTowikapc5y1zrDmkSgNyKo4pCkcyJCn0YGb2FBC4c/wBqvThtYTgwrR0MVtkMSrBrL6IilgavTvxNh'
          'iO9gWrtngHBrUkAt70qCBM="; session-id-time=2082787201l',
    }

SEARCH_PATH = 's?k='
