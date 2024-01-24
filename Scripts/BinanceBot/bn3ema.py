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

def cumul_ema_trend(price, fast_period, slow_period, span):
    fast_ema = calc_ema(price, fast_period)
    slow_ema = calc_ema(price, slow_period)
    div = [fast_ema[i] - slow_ema[i] for i in range(min(len(fast_ema), len(slow_ema)))]
    cumul_ema = sum(div[-span:])
    if cumul_ema > 0:
        return 'LONG'
    elif cumul_ema < 0:
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
            klines = get_klines(pair, mid_interval)
            cumul_trend = cumul_ema_trend(klines['close'], fast_period, slow_period, 100)
            # -1 index is the latest candle (not finish)
            ema_trend = check_ema(klines['close'], fast_period, mid_period, slow_period, -2)
            if cumul_trend == 'LONG' and ema_trend == 'LONG':
                long_count += 1
                klines = get_klines(pair, small_interval)
                small_mid_ema = calc_ema(klines['close'], 3*mid_period)
                small_slow_ema = calc_ema(klines['close'], 3*slow_period)
                check_low_mid = klines['low'][-2] < small_mid_ema[-2] and klines['low'][-3] > small_mid_ema[-3]
                check_low_slow = klines['low'][-2] < small_slow_ema[-2] and klines['low'][-3] > small_slow_ema[-3]
                if check_low_slow:    # downward breakout
                    filter_res += '{:<6}{:^14}{:>5}\n'.format('LONG', pair, 'SLOW')
                elif check_low_mid:
                    filter_res += '{:<6}{:^14}{:>5}\n'.format('LONG', pair, 'MID')
                else:
                    pass
            elif cumul_trend == 'SHORT' and ema_trend == 'SHORT':
                short_count += 1
                klines = get_klines(pair, small_interval)
                small_mid_ema = calc_ema(klines['close'], 3*mid_period)
                small_slow_ema = calc_ema(klines['close'], 3*slow_period)
                check_high_mid = klines['high'][-2] > small_mid_ema[-2] and klines['high'][-3] < small_mid_ema[-3]
                check_high_slow = klines['high'][-2] > small_slow_ema[-2] and klines['high'][-3] < small_slow_ema[-3]
                if check_high_slow:    # upward breakout
                    filter_res += '{:<6}{:^14}{:>5}\n'.format('SHORT', pair, 'SLOW')
                elif check_high_mid:
                    filter_res += '{:<6}{:^14}{:>5}\n'.format('SHORT', pair, 'MID')
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
        long_short_ratio = '\nL/S = ' + str(long_count) + '/' + str(short_count)
        error_info = '\nerror(s): ' + str(error_count) + '/' + str(len(all_pairs))
        message = '```\n' + filter_res + long_short_ratio + error_info + '\n```'
        sendMsg(message)


if __name__ == '__main__':
    # update pairs json file
    if time.localtime().tm_min == 0:
        update_pairs()

    # main function
    run()