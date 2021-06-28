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
EU_1h_12 = pd.read_csv('../Binance/ETHUSDT-1h-2020-12.csv').iloc[:,0:5]
EU_1h_01 = pd.read_csv('../Binance/ETHUSDT-1h-2021-01.csv').iloc[:,0:5]
EU_1h_02 = pd.read_csv('../Binance/ETHUSDT-1h-2021-02.csv').iloc[:,0:5]
EU_1h_03 = pd.read_csv('../Binance/ETHUSDT-1h-2021-03.csv').iloc[:,0:5]
EU_1h_04 = pd.read_csv('../Binance/ETHUSDT-1h-2021-04.csv').iloc[:,0:5]
EU_1h_05 = pd.read_csv('../Binance/ETHUSDT-1h-2021-05.csv').iloc[:,0:5]
EU_1h_12.columns = columns
EU_1h_01.columns = columns
EU_1h_02.columns = columns
EU_1h_03.columns = columns
EU_1h_04.columns = columns
EU_1h_05.columns = columns
EU_1h_6m = pd.concat([EU_1h_12,EU_1h_01,EU_1h_02,EU_1h_03,EU_1h_04,EU_1h_05],ignore_index=True)
close_price = EU_1h_6m['Close'].values.tolist()
open_price = EU_1h_6m['Open'].values.tolist()



# # 检测V形反转 (Frechet distance)
# price_range_init = close_price[:500]
# price_range = ema(price_range_init,5)
# global x,y,distance
# x = []
# y = []
# distance = []

# def v_detec(vtop,price_range):
# 	global x,y,distance
# 	for i in range(len(vtop),len(price_range)):
# 		test_list_init = price_range[i-len(vtop):i]
# 		test_list = [(x-min(test_list_init))/(max(test_list_init)-min(test_list_init)) for x in test_list_init]
# 		print(test_list)
# 		# if (math.sqrt(sum([(a - b)**2 for (a,b) in zip(vtop,test_list)])) < 0.5):
# 		if max([abs(a-b) for (a,b) in zip(vtop,test_list)]) < 0.3:
# 			x = x + [temp_x for temp_x in range(i-len(vtop),i)]
# 			y = y + [price_range_init[temp_y] for temp_y in range(i-len(vtop),i)]
# 		distance.append(max([abs(a-b) for (a,b) in zip(vtop,test_list)]))

# v_shape = [[3,2,1,2,3],[4,2,1,2,3]]
# for vtop_init in v_shape:
# 	vtop = [(x-min(vtop_init))/(max(vtop_init)-min(vtop_init)) for x in vtop_init]
# 	v_detec(vtop,price_range)

# # plt.plot(distance)
# plt.plot(price_range_init)
# plt.plot(price_range)
# plt.plot(x,y,'*')
# plt.show()



def backtest(fast_param,slow_param,param_comb,trend_param):
	balance = 100
	totalBalance = [balance]    # 收益曲线
	myShare = 0
	state = 'sleeping'
	win = 0    # 胜率统计
	loss = 0    # 胜率统计
	buy_points = []
	sell_points = []    # 买卖点统计
	for i in range(trend_param,len(close_price)):
		ema_fast = ema(close_price[:i],fast_param)
		ema_slow = ema(close_price[:i],slow_param)
		ema_trend = ema(close_price[:i],trend_param)
		ema_close = ema(close_price[:i],36)
		if ema_fast[-1] > max(ema_slow[-1],ema_trend[-1]):
			if (state == 'sleeping') and calc_slope(ema_trend[-5:]) > 0:
				state = 'bought'
				buy_price = close_price[i-1]    # 脚本每小时59分运行，粗略处理为以收盘价下单
				myShare = balance/buy_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				print('做多: '+str(buy_price))
				buy_points.append(i)
			# elif (state == 'sold') and calc_slope(ema_trend[-5:]) > 0:
			# 	state = 'bought'
			# 	buy_price = close_price[i-1]
			# 	profit = (sell_price-buy_price)*myShare
			# 	balance = sell_price*myShare+profit
			# 	myShare = balance/buy_price
			# 	totalBalance.append(balance)    # 收益曲线统计
			# 	balance = 0
			# 	if profit > 0:    # 胜率统计
			# 		win +=1
			# 	else:
			# 		loss += 1
			# 	print('平空做多: '+str(buy_price)+'  Profit: '+str(profit))
			# 	buy_points.append(i)
			else:
				pass
		elif ema_fast[-1] < min(ema_slow[-1],ema_trend[-1]):
			if (state == 'sleeping') and calc_slope(ema_trend[-5:]) < 0:
				state = 'sold'
				sell_price = close_price[i-1]
				myShare = balance/sell_price
				totalBalance.append(balance)    # 收益曲线统计
				balance = 0
				print('做空: '+str(sell_price))
				sell_points.append(i)
			# elif (state == 'bought') and calc_slope(ema_trend[-5:]) < 0:
			# 	state = 'sold'
			# 	sell_price = close_price[i-1]
			# 	profit = (sell_price-buy_price)*myShare
			# 	balance = buy_price*myShare+profit
			# 	myShare = balance/sell_price
			# 	totalBalance.append(balance)    # 收益曲线统计
			# 	balance = 0
			# 	if profit > 0:    # 胜率统计
			# 		win +=1
			# 	else:
			# 		loss += 1
			# 	print('平多做空: '+str(sell_price)+'  Profit: '+str(profit))
			# 	sell_points.append(i)
			else:
				pass
		elif (calc_slope(ema_close[-6:-1]) < 0) and (calc_slope(ema_close[-5:]) > 0) and (state == 'sold'):
			state = 'sleeping'
			buy_price = close_price[i-1]
			profit = (sell_price-buy_price)*myShare
			balance = sell_price*myShare+profit
			totalBalance.append(balance)    # 收益曲线统计
			myShare = 0
			if profit > 0:    # 胜率统计
				win +=1
			else:
				loss += 1
			print('平空: '+str(buy_price)+'  profit: '+str(profit))
			buy_points.append(i)
		elif (calc_slope(ema_close[-6:-1]) > 0) and (calc_slope(ema_close[-5:]) < 0) and (state == 'bought'):
			state = 'sleeping'
			sell_price = close_price[i-1]
			profit = (sell_price-buy_price)*myShare
			balance = buy_price*myShare+profit
			totalBalance.append(balance)    # 收益曲线统计
			myShare = 0
			if profit > 0:    # 胜率统计
				win +=1
			else:
				loss += 1
			print('平多: '+str(sell_price)+'  Profit: '+str(profit))
			sell_points.append(i)
		else:
			pass
	print('EMA'+str(fast_param)+'+EMA'+str(slow_param)+'+EMA'+str(trend_param)+': '+str(balance+myShare*close_price[-1])+'    平均交易间隔: '+str(6*30*24/len(totalBalance))+'    胜率: '+str(win/(win+loss)))
	totalBalance.append(balance+myShare*close_price[-1])    # 收益曲线统计
	# param_comb[int(str(fast_param)+str(slow_param))] = totalBalance[-1]    # 参数组合收益变化
	param_comb[int(str(fast_param)+str(slow_param)+str(trend_param))] = win/(win+loss)    # 参数组合胜率变化
	# plt.plot(totalBalance)
	plt.plot(close_price)
	plt.plot(ema(close_price,12),label='12')
	plt.plot(ema(close_price,144),label='144')
	plt.plot(ema(close_price,169),label='169')
	plt.legend()
	plt.vlines(buy_points,min(close_price),max(close_price),color='g')
	plt.vlines(sell_points,min(close_price),max(close_price),color='r')
	plt.show()



# 寻找最佳参数组合

# pool = multiprocessing.Pool(8)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for fast_param in range(9,10):
# 	for slow_param in range(55,56):
# 		for trend_param in range(64,65):
# 			pool.apply_async(backtest,(fast_param,slow_param,param_comb,trend_param,))

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





# # 在线版本
# def backtest(fast_param,slow_param,param_comb):
# 	balance = 100
# 	totalBalance = [balance]    # 收益曲线
# 	myShare = 0
# 	state = 'sleeping'
# 	win = 0    # 胜率统计
# 	loss = 0    # 胜率统计
# 	for i in range(fast_param+slow_param,len(close_price)):
# 		ema_fast = ema(close_price[:i],fast_param)
# 		ema_slow = ema(close_price[:i],slow_param)
# 		ema_trend = ema(close_price[:i],fast_param+slow_param)
# 		if ema_fast[-1] > ema_slow[-1]:
# 			if (state == 'sleeping') and (ema_fast[-1] > ema_trend[-1]) and (np.diff(ema_trend)[-1] < 0):
# 				state = 'bought'
# 				buy_price = close_price[i-1]    # 脚本每小时59分运行，粗略处理为以收盘价下单
# 				myShare = balance/buy_price
# 				totalBalance.append(balance)    # 收益曲线统计
# 				balance = 0
# 				print('做多: '+str(buy_price))
# 				buy_points.append(i)
# 			elif (state == 'sold') and (ema_fast[-1] > ema_trend[-1]) and (np.diff(ema_trend)[-1] < 0):
# 				state = 'bought'
# 				buy_price = close_price[i-1]
# 				profit = (sell_price-buy_price)*myShare
# 				balance = sell_price*myShare+profit
# 				myShare = balance/buy_price
# 				totalBalance.append(balance)    # 收益曲线统计
# 				balance = 0
# 				if profit > 0:    # 胜率统计
# 					win +=1
# 				else:
# 					loss += 1
# 				print('平空做多: '+str(buy_price)+'  Profit: '+str(profit))
# 				buy_points.append(i)
# 			elif state == 'sold':
# 				state = 'sleeping'
# 				buy_price = close_price[i-1]
# 				profit = (sell_price-buy_price)*myShare
# 				balance = sell_price*myShare+profit
# 				totalBalance.append(balance)    # 收益曲线统计
# 				myShare = 0
# 				if profit > 0:    # 胜率统计
# 					win +=1
# 				else:
# 					loss += 1
# 				print('平空: '+str(buy_price)+'  profit: '+str(profit))
# 				buy_points.append(i)
# 			else:
# 				pass
# 		elif ema_fast[-1] < ema_slow[-1]:
# 			if (state == 'sleeping') and (ema_fast[-1] < ema_trend[-1]) and (np.diff(ema_trend)[-1] < 0):
# 				state = 'sold'
# 				sell_price = close_price[i-1]
# 				myShare = balance/sell_price
# 				totalBalance.append(balance)    # 收益曲线统计
# 				balance = 0
# 				print('做空: '+str(sell_price))
# 				sell_points.append(i)
# 			elif (state == 'bought') and (ema_fast[-1] < ema_trend[-1]) and (np.diff(ema_trend)[-1] < 0):
# 				state = 'sold'
# 				sell_price = close_price[i-1]
# 				profit = (sell_price-buy_price)*myShare
# 				balance = buy_price*myShare+profit
# 				myShare = balance/sell_price
# 				totalBalance.append(balance)    # 收益曲线统计
# 				balance = 0
# 				if profit > 0:    # 胜率统计
# 					win +=1
# 				else:
# 					loss += 1
# 				print('平多做空: '+str(sell_price)+'  Profit: '+str(profit))
# 				sell_points.append(i)
# 			elif state == 'bought':
# 				state = 'sleeping'
# 				sell_price = close_price[i-1]
# 				profit = (sell_price-buy_price)*myShare
# 				balance = buy_price*myShare+profit
# 				totalBalance.append(balance)    # 收益曲线统计
# 				myShare = 0
# 				if profit > 0:    # 胜率统计
# 					win +=1
# 				else:
# 					loss += 1
# 				print('平多: '+str(sell_price)+'  Profit: '+str(profit))
# 				sell_points.append(i)
# 			else:
# 				pass
# 		else:
# 			pass
# 	print('EMA'+str(fast_param)+'+EMA'+str(slow_param)+': '+str(balance+myShare*close_price[-1])+'    平均交易间隔: '+str(6*30*24/len(totalBalance))+'    胜率: '+str(win/(win+loss)))
# 	totalBalance.append(balance+myShare*close_price[-1])    # 收益曲线统计
# 	# param_comb[int(str(fast_param)+str(slow_param))] = totalBalance[-1]    # 参数组合收益变化
# 	param_comb[int(str(fast_param)+str(slow_param))] = win/(win+loss)    # 参数组合胜率变化
# 	plt.plot(totalBalance)
# 	plt.show()

# backtest(9,55,{})