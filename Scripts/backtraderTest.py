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
EU_15m_1 = pd.read_csv('../Binance/ETHUSDT-15m-2021-05.csv').iloc[:,0:6]
EU_15m_2 = pd.read_csv('../Binance/ETHUSDT-15m-2021-06.csv').iloc[:,0:6]
EU_15m_3 = pd.read_csv('../Binance/ETHUSDT-15m-2021-07.csv').iloc[:,0:6]
EU_15m_1.columns = columns
EU_15m_2.columns = columns
EU_15m_3.columns = columns
EU_15m = pd.concat([EU_15m_1,EU_15m_2,EU_15m_3])
EU_15m.index = [dt.datetime.fromtimestamp(x/1000) for x in EU_15m.DateTime]

class SingleEMAStrategy(bt.Strategy):

	params = (
		('fast_param',3),
		('slow_param',6),
		('trend_param',250),
	)

	def log(self, txt, dt=None):
		dt = dt or self.datas[0].datetime.date(0)
		print('%s, %s' % (dt.isoformat(), txt))

	def __init__(self):
		self.ema_fast = bt.ind.EMA(period = self.params.fast_param)
		self.ema_slow = bt.ind.EMA(period = self.params.slow_param)
		self.ema_trend = bt.ind.EMA(period = self.params.trend_param)

	def notify_trade(self, trade):
		if not trade.isclosed:
			return

		self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
			(trade.pnl, trade.pnlcomm))

	# def next(self):
	# 	if not self.position:
	# 		if (self.ema_fast[-1] < self.ema_slow[-1]) and (self.ema_fast[0] > self.ema_slow[0]):
	# 			self.buy()
	# 			# self.log('SELL CREATE, %.2f' % self.data.close[0])
	# 		else:
	# 			pass
	# 	else:
	# 		if self.ema_fast[0] < self.ema_slow[0]:
	# 			self.close()
	# 		else:
	# 			pass

	# EMA250 breakout strategy
	def next(self):
		if not self.position:
			if (self.data.open[-1] > self.ema_trend[-1] > self.data.close[-1]) and (self.data.close[0] < self.ema_trend[0]):
				self.sell()
			else:
				pass
		else:
			if min(self.data.open[0],self.data.close[0]) > self.ema_trend[0]:
				self.close()
			else:
				pass


data = bt.feeds.PandasData(dataname=EU_15m)
cerebro = bt.Cerebro()
cerebro.addstrategy(SingleEMAStrategy)
cerebro.adddata(data)
cerebro.broker.setcash(10000)
cerebro.broker.setcommission(commission=0.0005)
cerebro.addsizer(bt.sizers.PercentSizer,percents=100)

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.plot(style='candle')



# 寻找最佳参数组合
# pool = multiprocessing.Pool(6)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for trend_param in range(10,200,5):
# 	pool.apply_async(Backtester(3,6).test,(trend_param,))

# pool.close()
# pool.join()

# result = dict(sorted(param_comb.items(), key=lambda x: x[0]))
# x_keys = []
# y_values = []
# for each in result.items():
# 	x_keys.append(str(each[0]))
# 	y_values.append(each[1])
# plt.plot(x_keys,y_values)
# ax = plt.axes()
# ax.xaxis.set_major_locator(plt.MultipleLocator(10))
# plt.show()