# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import json
import pandas as pd
import time
from teleBot import sendMsg
from fetchPairs import update_pairs
from config import Config



base_url = Config.BASE_URL
kline_url = Config.KLINE_URL

fast_period = Config.FAST_PERIOD
mid_period = Config.MID_PERIOD
slow_period = Config.SLOW_PERIOD

small_interval = Config.SMALL_INTERVAL
mid_interval = Config.MID_INTERVAL
large_interval = Config.LARGE_INTERVAL

pairs_path = Config.PAIRS_PATH

# proxies = {
# 'https': 'http://127.0.0.1:7890/',
# 'http': 'http://127.0.0.1:7890/'
# }

proxies = None


def read_all_pairs():
    with open(pairs_path, 'r') as f:
        all_pairs = json.load(f)
    return all_pairs

def get_klines(symbol, interval):
    url = base_url+kline_url+'?symbol='+symbol+'&interval='+interval
    res = requests.get(url, proxies=proxies)
    raw_data = json.loads(res.text)
    klines = {}
    klines['open'] = [float(each[1]) for each in raw_data]
    klines['high'] = [float(each[2]) for each in raw_data]
    klines['low'] = [float(each[3]) for each in raw_data]
    klines['close'] = [float(each[4]) for each in raw_data]
    klines['volume'] = [float(each[7]) for each in raw_data]
    return klines

def calc_ema(data, period):
    df = pd.DataFrame({'price':data})
    ema = df['price'].ewm(span=period, adjust=False, min_periods=period).mean().to_list()
    return ema

def check_ema(price, fast_period, mid_period, slow_period, shift):
    fast_ema = calc_ema(price, fast_period)[shift]
    mid_ema = calc_ema(price, mid_period)[shift]
    slow_ema = calc_ema(price, slow_period)[shift]
    if fast_ema > mid_ema > slow_ema:
        return 'LONG'
    elif fast_ema < mid_ema < slow_ema:
        return 'SHORT'
    else:
        return 'WAIT'

def run():
    filter_res = ''
    long_count = 0
    short_count = 0
    error_count = 0
    all_pairs = read_all_pairs()
    for pair in all_pairs:
        try:
            # print(str(all_pairs.index(pair)+1)+'/'+str(len(all_pairs)))
            klines = get_klines(pair, small_interval)
            close_price = klines['close'][:-1]    # delete the latest price (not finish)
            # trend starts just now
            ema_trend_1 = check_ema(close_price, fast_period, mid_period, slow_period, -1)
            ema_trend_2 = check_ema(close_price, fast_period, mid_period, slow_period, -2)
            if ema_trend_1 == 'LONG':
                long_count += 1
                if ema_trend_2 != 'LONG':    # indicate new long
                    klines = get_klines(pair, mid_interval)
                    close_price = klines['close'][:-1]
                    ema_trend = check_ema(close_price, fast_period, mid_period, slow_period, -1)
                    if ema_trend == 'LONG':
                        klines = get_klines(pair, large_interval)
                        close_price = klines['close'][:-1]
                        ema_trend = check_ema(close_price, fast_period, mid_period, slow_period, -1)
                        if ema_trend == 'LONG':
                            filter_res += ('LONG\t'+pair+'\n')
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            elif ema_trend_1 == 'SHORT':
                short_count += 1
                if ema_trend_2 != 'SHORT':    # new short
                    klines = get_klines(pair, mid_interval)
                    close_price = klines['close'][:-1]
                    ema_trend = check_ema(close_price, fast_period, mid_period, slow_period, -1)
                    if ema_trend == 'SHORT':
                        klines = get_klines(pair, large_interval)
                        close_price = klines['close'][:-1]
                        ema_trend = check_ema(close_price, fast_period, mid_period, slow_period, -1)
                        if ema_trend == 'SHORT':
                            filter_res += ('SHORT\t'+pair+'\n')
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except Exception as e:
            print(e)
            error_count += 1
        finally:
            continue
    if filter_res != '' or error_count > 10:
        long_short_ratio = '\nLONG/SHORT = ' + str(long_count) + '/' + str(short_count)
        error_info = '\nerror(s): ' + str(error_count) + '/' + str(len(all_pairs))
        message = filter_res + long_short_ratio + error_info
        sendMsg(message)


if __name__ == '__main__':
    # update pairs json file
    if time.localtime().tm_min == 0:
        update_pairs()

    # main function
    run()
