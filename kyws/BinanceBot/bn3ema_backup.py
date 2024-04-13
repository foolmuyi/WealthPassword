# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import json
import pandas as pd
import time
from teleBot import sendMsg



base_url = 'https://fapi.binance.com'
pairs_url = '/fapi/v1/exchangeInfo'
kline_url = '/fapi/v1/klines'

fast_period = 30
mid_period = 60
slow_period = 120

small_interval = '5m'
mid_interval = '15m'
large_interval = '30m'

min_volume_24h = 10000000    # 10 million USDT

# proxies = {
# 'https': 'http://127.0.0.1:7890/',
# 'http': 'http://127.0.0.1:7890/'
# }

proxies = None


def get_all_pairs(pairs_url):
    url = base_url + pairs_url
    res = requests.get(url, proxies=proxies)
    raw_data = json.loads(res.text)['symbols']
    pairs = [each['symbol'] for each in raw_data if (each['contractType']=='PERPETUAL' and each['quoteAsset']=='USDT')]
    return pairs

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

def check_ema(price, fast_period, mid_period, slow_period):
    fast_ema = calc_ema(price, fast_period)[-1]
    mid_ema = calc_ema(price, mid_period)[-1]
    slow_ema = calc_ema(price, slow_period)[-1]
    if fast_ema > mid_ema > slow_ema:
        return 'LONG'
    elif fast_ema < mid_ema < slow_ema:
        return 'SHORT'
    else:
        return 'WAIT'

def run():
    filter_res = ''
    error_count = 0
    all_pairs = get_all_pairs(pairs_url)
    for pair in all_pairs:
        try:
            # print(str(all_pairs.index(pair)+1)+'/'+str(len(all_pairs)))
            klines = get_klines(pair, small_interval)
            volume_usdt_24h = sum(klines['volume'][-288:])
            if volume_usdt_24h > min_volume_24h:
                close_price = klines['close'][:-1]    # delete the latest price (not finish)
                last_high = klines['high'][-2]    # get the high price of the latest finished candle
                last_low = klines['low'][-2]
                last_ema_slow = calc_ema(close_price, slow_period)[-1]
                ema_trend = check_ema(close_price, fast_period, mid_period, slow_period)
                if ema_trend == 'LONG' and last_low < last_ema_slow and last_high > last_ema_slow:
                    klines = get_klines(pair, mid_interval)
                    close_price = klines['close'][:-1]
                    ema_trend = check_ema(close_price, fast_period, mid_period, slow_period)
                    if ema_trend == 'LONG':
                        klines = get_klines(pair, large_interval)
                        close_price = klines['close'][:-1]
                        ema_trend = check_ema(close_price, fast_period, mid_period, slow_period)
                        if ema_trend == 'LONG':
                            filter_res += ('LONG\t'+pair+'\n')
                        else:
                            pass
                    else:
                        pass
                elif ema_trend == 'SHORT' and last_high > last_ema_slow and last_low < last_ema_slow:
                    klines = get_klines(pair, mid_interval)
                    close_price = klines['close'][:-1]
                    ema_trend = check_ema(close_price, fast_period, mid_period, slow_period)
                    if ema_trend == 'SHORT':
                        klines = get_klines(pair, large_interval)
                        close_price = klines['close'][:-1]
                        ema_trend = check_ema(close_price, fast_period, mid_period, slow_period)
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
        message = filter_res + '\nerrors: ' + str(error_count) + '/' + str(len(all_pairs))
        sendMsg(message)


if __name__ == '__main__':
    run()
