# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import requests
import json
import time
import datetime
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing


def ma(data,period=5,weights='default'):
	if period <= 0:
		raise IndexError('Period is '+str(period)+', which is less than 1')
	elif len(data) < period:
		raise IndexError('Cannot obtain MA because the length of the list is '+str(len(data))+' while the period is '+str(period))
	elif (weights != 'default' and len(weights) != period):
		raise IndexError('The length of weight list is '+str(len(weights))+' while the period is '+str(period))
	else:
		weights = [1 for _ in range(period)] if weights=='default' else weights
		ma_list = [data[i] if i<period-1 else np.sum(np.array(data[i-period+1:i+1])*np.array(weights))/np.sum(weights) for i in range(len(data))]
		return ma_list

def ema(data,period):
	if period <= 0:
		raise IndexError('Period is '+str(period)+', which is less than 1')
	elif len(data) < period:
		raise IndexError('Cannot obtain EMA because the length of the data list is '+str(len(data))+' while the period is '+str(period))
	else:
		ema_list = []
		for i in range(len(data)):
			if i == 0:
				ema_list.append(round(data[0],2))
			else:
				ema_today = (2*data[i]+(period-1)*ema_list[i-1])/(period+1)
				ema_list.append(round(ema_today,2))
	return ema_list

def calc_slope(data_list):
	n = len(data_list)
	xy_bar = sum([i*data_list[i] for i in range(n)])/n
	x_bar = sum(range(n))/n
	y_bar = sum(data_list)/n
	x_squa_bar = sum([i**2 for i in range(n)])/n
	k = (xy_bar-x_bar*y_bar)/(x_squa_bar-x_bar**2)
	return k



columns = ['OpenTime','Open','High','Low','Close']
EU_15m_12 = pd.read_csv('../Binance/ETHUSDT-15m-2020-12.csv').iloc[:,0:5]
EU_15m_01 = pd.read_csv('../Binance/ETHUSDT-15m-2021-01.csv').iloc[:,0:5]
EU_15m_02 = pd.read_csv('../Binance/ETHUSDT-15m-2021-02.csv').iloc[:,0:5]
EU_15m_03 = pd.read_csv('../Binance/ETHUSDT-15m-2021-03.csv').iloc[:,0:5]
EU_15m_04 = pd.read_csv('../Binance/ETHUSDT-15m-2021-04.csv').iloc[:,0:5]
EU_15m_05 = pd.read_csv('../Binance/ETHUSDT-15m-2021-05.csv').iloc[:,0:5]
EU_15m_12.columns = columns
EU_15m_01.columns = columns
EU_15m_02.columns = columns
EU_15m_03.columns = columns
EU_15m_04.columns = columns
EU_15m_05.columns = columns
EU_15m_6m = pd.concat([EU_15m_12,EU_15m_01,EU_15m_02,EU_15m_03,EU_15m_04,EU_15m_05],ignore_index=True)
close_price = EU_15m_6m['Close'].values.tolist()
open_price = EU_15m_6m['Open'].values.tolist()
high_price = EU_15m_6m['High'].values.tolist()
low_price = EU_15m_6m['Low'].values.tolist()

class Backtester(object):

	def __init__(self,fast_param,slow_param):
		self.fast_param = fast_param
		self.slow_param = slow_param
		self.balance = 100
		self.totalBalance = [self.balance]    # 收益曲线
		self.myShare = 0
		self.state = 'sleeping'
		self.win = 0    # 胜率统计
		self.loss = 0    # 胜率统计
		self.buy_points = []
		self.sell_points = []
		self.close_points = []    # 买卖点统计

	def buyLong(self,i):
		self.state = 'bought'
		self.buy_price = close_price[i-1]    # 脚本每小时59分运行，粗略处理为以收盘价下单
		self.myShare = self.balance/self.buy_price
		self.balance = 0
		print('做多: '+str(self.buy_price))
		self.buy_points.append(i)

	def closeLong(self,i):
		self.state = 'sleeping'
		self.close_long_price = close_price[i-1]
		profit = (self.close_long_price-self.buy_price)*self.myShare-self.buy_price*self.myShare*0.00007
		# profit = (self.close_long_price-self.buy_price)*self.myShare
		self.balance = self.buy_price*self.myShare+profit
		self.totalBalance.append(self.balance)    # 收益曲线统计
		self.myShare = 0
		if profit > 0:    # 胜率统计
			self.win +=1
		else:
			self.loss += 1
		print('平多: '+str(self.close_long_price)+'  Profit: '+str(profit))
		self.close_points.append(i)

	def sellShort(self,i):
		self.state = 'sold'
		self.sell_price = close_price[i-1]
		self.myShare = self.balance/self.sell_price
		self.balance = 0
		print('做空: '+str(self.sell_price))
		self.sell_points.append(i)

	def closeShort(self,i):
		self.state = 'sleeping'
		self.close_short_price = close_price[i-1]
		profit = (self.sell_price-self.close_short_price)*self.myShare-self.sell_price*self.myShare*0.00007
		# profit = (self.sell_price-self.close_short_price)*self.myShare
		self.balance = self.sell_price*self.myShare+profit
		self.totalBalance.append(self.balance)    # 收益曲线统计
		self.myShare = 0
		if profit > 0:    # 胜率统计
			self.win +=1
		else:
			self.loss += 1
		print('平空: '+str(self.close_short_price)+'  profit: '+str(profit))
		self.close_points.append(i)

	def test(self):
		for i in range(self.slow_param,len(close_price)):
			ema_fast = ema(close_price[:i],self.fast_param)
			ema_slow = ema(close_price[:i],self.slow_param)

			if self.state == 'bought':
				if ema_fast[-1] < ema_slow[-1]:
					self.closeLong(i)
				elif (close_price[i-1]-self.buy_price)/self.buy_price < -0.003:
					self.closeLong(i) 
				elif (close_price[i-1]-self.buy_price)/self.buy_price > 0.003:
					self.closeLong(i)
			elif self.state == 'sold':
				if ema_fast[-1] > ema_slow[-1]:
					self.closeShort(i)
				elif (close_price[i-1]-self.sell_price)/self.sell_price < -0.003:
					self.closeShort(i)
				elif (close_price[i-1]-self.sell_price)/self.sell_price > 0.003:
					self.closeShort(i)
			else:
				pass

			# 建仓
			if (ema_fast[-2] < ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1]) and (self.state == 'sleeping'):
				self.buyLong(i)
			elif (ema_fast[-2] > ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1]) and (self.state == 'sleeping'):
				self.sellShort(i)
			else:
				pass
		print('EMA'+str(self.fast_param)+'+EMA'+str(self.slow_param)+': '+str(self.balance+self.myShare*close_price[-1])
			+'    平均交易间隔: '+str(6*30*24/len(self.totalBalance))+'    胜率: '+str(self.win/(self.win+self.loss)))

	def show_plot(self):
		if self.state == 'bought':
			profit = (close_price[-1]-self.buy_price)*self.myShare
			self.balance = self.buy_price*self.myShare+profit
			self.totalBalance.append(self.balance)    # 收益曲线统计
		elif self.state == 'sold':
			profit = (self.sell_price-close_price[-1])*self.myShare
			self.balance = self.sell_price*self.myShare+profit
			self.totalBalance.append(self.balance)    # 收益曲线统计
		else:
			pass    # 收益曲线统计
		# param_comb[int(str(test_param)+str(fast_param)+str(slow_param))] = totalBalance[-1]    # 参数组合收益变化
		# param_comb[int(str(self.fast_param)+str(self.slow_param)+str(self.trend_param))] = self.win/(self.win+self.loss)    # 参数组合胜率变化
		plt.plot(self.totalBalance)
		# plt.plot(close_price)
		# plt.plot(ema(close_price,self.test_param),label='TEST')
		# plt.plot(ema(close_price,self.fast_param),label='FAST')
		# plt.plot(ema(close_price,self.slow_param),label='SLOW')
		# plt.plot(ema(close_price,self.trend_param),label='TREND')
		# plt.legend()
		# plt.vlines(self.buy_points,min(close_price),max(close_price),color='g')    # 做多点
		# plt.vlines(self.sell_points,min(close_price),max(close_price),color='r')    # 做空点
		# plt.vlines(self.close_points,min(close_price),max(close_price),color='orange')    # 平仓点
		plt.show()


tester = Backtester(3,6)
tester.test()
tester.show_plot()



# 寻找最佳参数组合
# pool = multiprocessing.Pool(6)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for fast_param in range(25,35):
# 	for slow_param in range(fast_param+3,fast_param+13):
# 		pool.apply_async(backtest,(test_param,fast_param,slow_param,param_comb,))

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