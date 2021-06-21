# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os,requests,json
import time,datetime
import pandas as pd
import numpy as np


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

columns = ['OpenTime','Open','High','Low','Close']
EU_1h_12 = pd.read_csv('./ETHUSDT-1h-2020-12.csv').iloc[:,0:5]
EU_1h_01 = pd.read_csv('./ETHUSDT-1h-2021-01.csv').iloc[:,0:5]
EU_1h_02 = pd.read_csv('./ETHUSDT-1h-2021-02.csv').iloc[:,0:5]
EU_1h_03 = pd.read_csv('./ETHUSDT-1h-2021-03.csv').iloc[:,0:5]
EU_1h_04 = pd.read_csv('./ETHUSDT-1h-2021-04.csv').iloc[:,0:5]
EU_1h_05 = pd.read_csv('./ETHUSDT-1h-2021-05.csv').iloc[:,0:5]
EU_1h_12.columns = columns
EU_1h_01.columns = columns
EU_1h_02.columns = columns
EU_1h_03.columns = columns
EU_1h_04.columns = columns
EU_1h_05.columns = columns
EU_1h_6m = pd.concat([EU_1h_12,EU_1h_01,EU_1h_02,EU_1h_03,EU_1h_04,EU_1h_05],ignore_index=True)
close_price = EU_1h_6m['Close'].values.tolist()
open_price = EU_1h_6m['Open'].values.tolist()
for fast_param in range(3,24):
	for slow_param in range(fast_param+1,24):
		balance = 100
		myShare = 0
		num = 0
		state = 'sleeping'
		for i in range(slow_param+fast_param,len(close_price)):
			ema_fast = ema(close_price[:i],fast_param)
			ema_slow = ema(close_price[:i],slow_param)
			ema_indicator = ema(close_price[:i],slow_param+fast_param)
			if (ema_fast[-2] < ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1]) and (np.diff(ema_slow)[-1]>0):
				if (state == 'sleeping') and (np.diff(ema_indicator)[-1]>0):
					state = 'bought'
					buy_price = (close_price[i+1]+open_price[i+1])/2
					myShare = balance/buy_price
					balance = 0
					num += 1
					# print('做多: '+str(buy_price))
				elif (state == 'sold') and (np.diff(ema_indicator)[-1]>0):
					state = 'bought'
					buy_price = (close_price[i+1]+open_price[i+1])/2
					profit = (sell_price-buy_price)*myShare
					balance = buy_price*myShare+profit
					myShare = balance/buy_price
					balance = 0
					num += 1
					# print('平空做多: '+str(buy_price))
				elif state == 'sold':
					state = 'sleeping'
					buy_price = (close_price[i+1]+open_price[i+1])/2
					profit = (sell_price-buy_price)*myShare
					balance = buy_price*myShare+profit
					myShare = 0
					num += 1
					# print('平空: '+str(buy_price)+'  profit: '+str(profit))
				else:
					pass
			elif (ema_fast[-2] > ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1]) and (np.diff(ema_slow)[-1]<0):
				if (state == 'sleeping') and (np.diff(ema_indicator)[-1]<0):
					state = 'sold'
					sell_price = (close_price[i+1]+open_price[i+1])/2
					myShare = balance/sell_price
					balance = 0
					num += 1
					# print('做空: '+str(sell_price))
				elif (state == 'bought') and (np.diff(ema_indicator)[-1]<0):
					state = 'sold'
					sell_price = (close_price[i+1]+open_price[i+1])/2
					profit = (sell_price-buy_price)*myShare
					balance = sell_price*myShare+profit
					myShare = balance/sell_price
					balance = 0
					num += 1
					# print('平多做空: '+str(sell_price)+'  Profit: '+str(profit))
				elif state == 'bought':
					state = 'sleeping'
					sell_price = (close_price[i+1]+open_price[i+1])/2
					profit = (sell_price-buy_price)*myShare
					balance = sell_price*myShare+profit
					myShare = 0
					num += 1
					# print('平多: '+str(sell_price)+'  Profit: '+str(profit))
				else:
					pass
		print('EMA'+str(fast_param)+'+EMA'+str(slow_param)+': '+str(balance+myShare*close_price[-1])+'    平均持仓时间： '+str(6*30*24/num))

# EMA24+EMA30: 2100+