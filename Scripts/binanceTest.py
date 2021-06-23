# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os,requests,json
import time,datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing


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


def backtest(fast_param,slow_param,param_comb):
	balance = 100
	totalBalance = [balance]    # 收益曲线
	myShare = 0
	state = 'sleeping'
	win = 0    # 胜率统计
	loss = 0    # 胜率统计
	for i in range(fast_param+slow_param,len(close_price)):
		ema_fast = ema(close_price[:i],fast_param)
		ema_slow = ema(close_price[:i],slow_param)
		ema_indicator = ema(close_price[:i],slow_param+fast_param)
		if (ema_fast[-2] < ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1]) and (np.diff(ema_slow)[-1]>0):
			if (state == 'sleeping') and (np.diff(ema_indicator)[-1]>0):
				state = 'bought'
				buy_price = (close_price[i+1]+open_price[i+1])/2
				myShare = balance/buy_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				print('做多: '+str(buy_price))
			elif (state == 'sold') and (np.diff(ema_indicator)[-1]>0):
				state = 'bought'
				buy_price = (close_price[i+1]+open_price[i+1])/2
				profit = (sell_price-buy_price)*myShare
				balance = buy_price*myShare+profit
				myShare = balance/buy_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				if profit > 0:    # 胜率统计
					win +=1
				else:
					loss += 1
				print('平空做多: '+str(buy_price)+'  Profit: '+str(profit))
			elif state == 'sold':
				state = 'sleeping'
				buy_price = (close_price[i+1]+open_price[i+1])/2
				profit = (sell_price-buy_price)*myShare
				balance = buy_price*myShare+profit
				totalBalance.append(balance)    # 收益曲线统计
				myShare = 0
				if profit > 0:    # 胜率统计
					win +=1
				else:
					loss += 1
				print('平空: '+str(buy_price)+'  profit: '+str(profit))
			else:
				pass
		elif (ema_fast[-2] > ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1]) and (np.diff(ema_slow)[-1]<0):
			if (state == 'sleeping') and (np.diff(ema_indicator)[-1]<0):
				state = 'sold'
				sell_price = (close_price[i+1]+open_price[i+1])/2
				myShare = balance/sell_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				print('做空: '+str(sell_price))
			elif (state == 'bought') and (np.diff(ema_indicator)[-1]<0):
				state = 'sold'
				sell_price = (close_price[i+1]+open_price[i+1])/2
				profit = (sell_price-buy_price)*myShare
				balance = sell_price*myShare+profit
				myShare = balance/sell_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				if profit > 0:    # 胜率统计
					win +=1
				else:
					loss += 1
				print('平多做空: '+str(sell_price)+'  Profit: '+str(profit))
			elif state == 'bought':
				state = 'sleeping'
				sell_price = (close_price[i+1]+open_price[i+1])/2
				profit = (sell_price-buy_price)*myShare
				balance = sell_price*myShare+profit
				totalBalance.append(balance)    # 收益曲线统计
				myShare = 0
				if profit > 0:    # 胜率统计
					win +=1
				else:
					loss += 1
				print('平多: '+str(sell_price)+'  Profit: '+str(profit))
			else:
				pass
	print('EMA'+str(fast_param)+'+EMA'+str(slow_param)+': '+str(balance+myShare*close_price[-1])+'    平均交易间隔: '+str(6*30*24/len(totalBalance))+'    胜率: '+str(win/(win+loss)))
	totalBalance.append(balance+myShare*close_price[-1])    # 收益曲线统计
	# param_comb[int(str(fast_param)+str(slow_param))] = totalBalance[-1]    # 参数组合收益变化
	param_comb[int(str(fast_param)+str(slow_param))] = win/(win+loss)    # 参数组合胜率变化
	plt.plot(totalBalance)
	plt.show()


backtest(3,52,{})


# 寻找最佳参数组合

# pool = multiprocessing.Pool(8)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for fast_param in range(3,13):
# 	for slow_param in range(30,55):
# 		pool.apply_async(backtest,(fast_param,slow_param,param_comb,))

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

