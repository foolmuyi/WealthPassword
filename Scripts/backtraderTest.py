# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import requests
import json
import time
import datetime as dt
import math
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing


columns = ['DateTime','Open','High','Low','Close','Volume']
EU_5m_1 = pd.read_csv('../Binance/ETHUSDT-5m-2021-05.csv').iloc[:,0:6]
EU_5m_2 = pd.read_csv('../Binance/ETHUSDT-5m-2021-06.csv').iloc[:,0:6]
EU_5m_3 = pd.read_csv('../Binance/ETHUSDT-5m-2021-07.csv').iloc[:,0:6]
EU_5m_1.columns = columns
EU_5m_2.columns = columns
EU_5m_3.columns = columns
EU_5m = pd.concat([EU_5m_1,EU_5m_2,EU_5m_3])
EU_5m.index = [dt.datetime.fromtimestamp(x/1000) for x in EU_5m.DateTime]

class SingleEMAStrategy(bt.Strategy):

    params = (
        ('fast_param',3),
        ('slow_param',6),
        ('trend_param',550),
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.ema_fast = bt.ind.EMA(period = self.params.fast_param)
        self.ema_slow = bt.ind.EMA(period = self.params.slow_param)
        self.ema_trend = bt.ind.EMA(period = self.params.trend_param)
        # self.order = None

    def notify_trade(self, trade):
      if not trade.isclosed:
          return

      self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    # def notify_order(self, order):
    #     if order.status in [order.Submitted, order.Accepted]:
    #     # Buy/Sell order submitted/accepted to/by broker - Nothing to do
    #         return

    #     # Check if an order has been completed
    #     # Attention: broker could reject order if not enough cash
    #     if order.status in [order.Completed]:
    #         if order.isbuy():
    #             self.log('BUY EXECUTED, %.2f' % order.executed.price)
    #         elif order.issell():
    #             self.log('SELL EXECUTED, %.2f' % order.executed.price)

    #         self.bar_executed = len(self)

    #     elif order.status in [order.Canceled, order.Margin, order.Rejected]:
    #         self.log('Order Canceled/Margin/Rejected')

    #     # Write down: no pending order
    #     self.order = None

    # EMA250 breakout strategy
    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        # if self.order:
        #     return

        if not self.position:
            if (self.data.open[-1] > self.ema_trend[-1] > self.data.close[-1]) and (max(self.data.open[0],self.data.close[0]) < self.ema_trend[0]):
              self.sell()
            # elif (self.data.open[-1] < self.ema_trend[-1] < self.data.close[-1]) and (min(self.data.open[0],self.data.close[0]) > self.ema_trend[0]):
            #     self.buy()
            else:
                pass
        else:
            if (self.position.size < 0 ) and (min(self.data.open[0],self.data.close[0]) > self.ema_trend[0]):
                self.close()
            #     self.buy()
            # elif (self.position.size > 0 ) and (max(self.data.open[0],self.data.close[0]) < self.ema_trend[0]):
            #     self.close()
            #     self.sell()
            else:
                pass

    # def stop(self):
    #   self.log('(EMA Period %2d) Ending Value %.2f' % (self.params.trend_param, self.broker.getvalue()))


data = bt.feeds.PandasData(dataname=EU_5m)
cerebro = bt.Cerebro()
cerebro.addstrategy(SingleEMAStrategy)
# cerebro.optstrategy(SingleEMAStrategy,trend_param=range(600,700,10))
cerebro.adddata(data)
cerebro.broker.setcash(100)
cerebro.broker.setcommission(commission=0.0005)
cerebro.addsizer(bt.sizers.PercentSizer,percents=80)

# print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.plot(style='candle')



# 寻找最佳参数组合
# pool = multiprocessing.Pool(6)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for trend_param in range(10,200,5):
#   pool.apply_async(Backtester(3,6).test,(trend_param,))

# pool.close()
# pool.join()

# result = dict(sorted(param_comb.items(), key=lambda x: x[0]))
# x_keys = []
# y_values = []
# for each in result.items():
#   x_keys.append(str(each[0]))
#   y_values.append(each[1])
# plt.plot(x_keys,y_values)
# ax = plt.axes()
# ax.xaxis.set_major_locator(plt.MultipleLocator(10))
# plt.show()