# !/usr/bin/env python3
# -*- coding: utf-8 -*-


class Config:
    # url configs
    BASE_URL = 'https://fapi.binance.com'
    PAIRS_URL = '/fapi/v1/exchangeInfo'
    KLINE_URL = '/fapi/v1/klines'
    DAILY_CHANGE_URL = '/fapi/v1/ticker/24hr'

    # EMA period configs
    FAST_PERIOD = 30
    MID_PERRIOD = 60
    SLOW_PERIOD = 120

    # timeframe configs
    SMALL_INTERVAL = '5m'
    MID_INTERVAL = '15m'
    LARGE_INTERVAL = '30m'

    # volume filter configs
    MIN_VOL_24H = 15000000    # 15 million USDT

    # pairs.json path
    PAIRS_PATH = './pairs.json'