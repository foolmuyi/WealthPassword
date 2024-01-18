# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import json
from config import Config


# proxies = {
# 'https': 'http://127.0.0.1:7890/',
# 'http': 'http://127.0.0.1:7890/'
# }

proxies = None


def get_all_pairs(base_url, pairs_url):
    url = base_url + pairs_url
    res = requests.get(url, proxies=proxies)
    raw_data = json.loads(res.text)['symbols']
    pairs = [each['symbol'] for each in raw_data if (each['contractType']=='PERPETUAL' and each['quoteAsset']=='USDT')]
    return pairs

def get_24hr_change(base_url, daily_change_url):
    url = base_url + daily_change_url
    res = requests.get(url, proxies=proxies)
    data = json.loads(res.text)
    return data

def update_pairs():
    all_usdt_pairs = get_all_pairs(Config.BASE_URL, Config.PAIRS_URL)
    daily_change = get_24hr_change(Config.BASE_URL, Config.DAILY_CHANGE_URL)
    selected_pairs = [each['symbol'] for each in daily_change if (each['symbol'] 
        in all_usdt_pairs and float(each['quoteVolume']) > Config.MIN_VOL_24H)]

    with open(Config.PAIRS_PATH, 'w') as f:
        json.dump(selected_pairs, f)