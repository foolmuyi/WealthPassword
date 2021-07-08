# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import json
import requests
import time
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d
import alchemist as am
import multiprocessing


class Backtester(object):
	def __init__(self,fund_code,start_date,end_date):
		self.balance = 5000
		self.myShares = 0
		self.buy_date = []
		self.sell_date = []
		self.fund_code = fund_code
		self.start_date = start_date
		self.end_date = end_date

	def readFile(self):
		file_path = '../Data/'+self.fund_code+'.csv'
		df = pd.read_csv(file_path)
		df['Date'] = pd.to_datetime(df['Date'])
		df = df.set_index('Date')
		df = df[self.start_date:self.end_date]
		self.accWorth_series = pd.Series(df['AccWorth'], index=df.index)

	def getTomoPrice(self):
		tomo_index = len(self.accWorth_series[:self.today])    # 注意不需要+1，因为index从0开始
		if tomo_index == len(self.accWorth_series):    # 已是最后一天
			tomo = self.today
			tomo_price = self.accWorth_series[str(self.today)]    # 近似以当日净值结算
		else:
			tomo = str(self.accWorth_series.index[tomo_index]).split(' ')[0]    # 获取下一个交易日的日期
			tomo_price = self.accWorth_series[self.accWorth_series.index[tomo_index]]    # 以下一个交易日的净值结算
		return tomo,tomo_price

	def Buy(self):
		if self.balance > 0:
			tomo,tomo_accWorth = self.getTomoPrice()
			self.myShares += self.balance/tomo_accWorth
			# print('Buy '+str(self.balance)+' on '+str(tomo))
			self.balance = 0
			self.buy_date.append(tomo)

	def Sell(self):
		if self.myShares > 0:
			tomo,tomo_accWorth = self.getTomoPrice()
			sell_amount = round(self.myShares*tomo_accWorth*0.995,2)    # 粗略假设手续费0.5%
			sell_amount = round(self.myShares*tomo_accWorth,2)
			self.balance += sell_amount
			# print('Sell '+str(sell_amount)+' on '+str(tomo))
			self.myShares = 0
			self.sell_date.append(tomo)

	def show_plot(self,fast_param,slow_param):
		ema_fast = am.ema(self.accWorth_series.tolist(),fast_param)
		ema_fast_series = pd.Series(ema_fast,index=self.accWorth_series.index)
		ema_fast_series.plot(color='orange')
		ema_slow = am.ema(self.accWorth_series.tolist(),slow_param)
		ema_slow_series = pd.Series(ema_slow,index=self.accWorth_series.index)
		ema_slow_series.plot(color='purple')
		self.accWorth_series.plot()
		plt.vlines(self.buy_date,min(self.accWorth_series),max(self.accWorth_series),color='g')
		plt.vlines(self.sell_date,min(self.accWorth_series),max(self.accWorth_series),color='r')
		plt.show()

	def test(self,fast_param,slow_param):
		self.readFile()
		for i in range((self.end_date-self.start_date).days):
			self.today = self.start_date+datetime.timedelta(days=i)
			signal = am.getSignal(self.fund_code,self.today,fast_param,slow_param)
			if signal == 'Buy':
				self.Buy()
			elif signal == 'Sell':
				self.Sell()
		print('Total balance: '+str(self.balance+self.myShares*self.accWorth_series[str(self.today)]))
		print('Total ratio of return: '+str(round(((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000,2)))
		try:
			r_ratio = round(((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000,2)
			return r_ratio
		except:
			return 0


code_list = ['512290','512760','512400','513050','510300','510050','159949','512170','512480','512690']
start_date = datetime.date(2019,9,3)
end_date = datetime.date(2021,7,1)

fund_code = '512690'
tester1 = Backtester(fund_code,start_date,end_date)
tester1.test(12,21)
tester1.show_plot(12,21)

# def run(code_list,start_date,end_date,fast_param,slow_param):
# 	ratio_avg = 0
# 	for fund_code in code_list:
# 		try:
# 			tester1 = Backtester(fund_code,start_date,end_date)
# 			ratio_avg += tester1.test(fast_param,slow_param)
# 		except Exception as e:
# 			print(fund_code)
# 			print(e)
# 	ratio_avg = ratio_avg/len(code_list)
# 	print('{}{}+{}{}: {:.2f}'.format('EMA',fast_param,'EMA',slow_param,ratio_avg))

# pool = multiprocessing.Pool(6)
# manager = multiprocessing.Manager()

# for fast_param in range(3,20):
# 	for slow_param in range(fast_param+1,fast_param+20,2):
# 		pool.apply_async(run,(code_list,start_date,end_date,fast_param,slow_param,))

# pool.close()
# pool.join()

# ratio_ref = 0
# for fund_code in code_list:
# 	file_path = '../Data/'+fund_code+'.csv'
# 	df = pd.read_csv(file_path)
# 	df['Date'] = pd.to_datetime(df['Date'])
# 	df = df.set_index('Date')
# 	accWorth_series = pd.Series(df['AccWorth'], index=df.index)
# 	ratio_ref += (accWorth_series[str(end_date)]-accWorth_series[str(start_date)])/accWorth_series[str(start_date)]
# print('{}: {:.2f}'.format('ref',ratio_ref/len(code_list)))


# EMA3+EMA6: 0.37
# EMA3+EMA8: 0.45
# EMA3+EMA10: 0.47
# EMA3+EMA14: 0.50
# EMA3+EMA12: 0.46
# EMA3+EMA4: 0.42
# EMA3+EMA18: 0.52
# EMA3+EMA16: 0.48
# EMA3+EMA20: 0.55
# EMA4+EMA7: 0.47
# EMA3+EMA22: 0.54
# EMA4+EMA5: 0.54
# EMA4+EMA9: 0.48
# EMA4+EMA11: 0.46
# EMA4+EMA13: 0.50
# EMA4+EMA17: 0.47
# EMA4+EMA15: 0.50
# EMA4+EMA19: 0.53
# EMA4+EMA21: 0.51
# EMA4+EMA23: 0.57
# EMA5+EMA10: 0.58
# EMA5+EMA6: 0.58
# EMA5+EMA8: 0.55
# EMA5+EMA12: 0.52
# EMA5+EMA14: 0.57
# EMA5+EMA16: 0.57
# EMA5+EMA22: 0.62
# EMA5+EMA18: 0.57
# EMA5+EMA20: 0.62
# EMA5+EMA24: 0.65
# EMA6+EMA9: 0.53
# EMA6+EMA7: 0.57
# EMA6+EMA11: 0.52
# EMA6+EMA13: 0.58
# EMA6+EMA15: 0.61
# EMA6+EMA17: 0.51
# EMA6+EMA19: 0.65
# EMA6+EMA21: 0.65
# EMA6+EMA23: 0.67
# EMA6+EMA25: 0.66
# EMA7+EMA8: 0.46
# EMA7+EMA10: 0.53
# EMA7+EMA14: 0.61
# EMA7+EMA12: 0.53
# EMA7+EMA16: 0.61
# EMA7+EMA18: 0.62
# EMA7+EMA22: 0.63
# EMA7+EMA20: 0.68
# EMA7+EMA24: 0.65
# EMA7+EMA26: 0.65
# EMA8+EMA9: 0.56
# EMA8+EMA11: 0.58
# EMA8+EMA13: 0.54
# EMA8+EMA15: 0.55
# EMA8+EMA19: 0.68
# EMA8+EMA21: 0.66
# EMA8+EMA17: 0.58
# EMA8+EMA23: 0.62
# EMA8+EMA25: 0.67
# EMA8+EMA27: 0.66
# EMA9+EMA10: 0.63
# EMA9+EMA12: 0.63
# EMA9+EMA14: 0.56
# EMA9+EMA20: 0.68
# EMA9+EMA16: 0.58
# EMA9+EMA18: 0.66
# EMA9+EMA22: 0.62
# EMA9+EMA24: 0.69
# EMA9+EMA26: 0.66
# EMA9+EMA28: 0.69
# EMA10+EMA11: 0.60
# EMA10+EMA13: 0.72
# EMA10+EMA15: 0.57
# EMA10+EMA19: 0.64
# EMA10+EMA17: 0.60
# EMA10+EMA21: 0.70
# EMA10+EMA23: 0.67
# EMA10+EMA25: 0.65
# EMA10+EMA27: 0.67
# EMA11+EMA12: 0.43
# EMA10+EMA29: 0.62
# EMA11+EMA14: 0.63
# EMA11+EMA18: 0.66
# EMA11+EMA16: 0.61
# EMA11+EMA20: 0.62
# EMA11+EMA22: 0.64
# EMA11+EMA24: 0.65
# EMA11+EMA26: 0.61
# EMA11+EMA28: 0.63
# EMA11+EMA30: 0.60
# EMA12+EMA13: 0.58
# EMA12+EMA15: 0.66
# EMA12+EMA17: 0.67
# EMA12+EMA21: 0.72
# EMA12+EMA19: 0.64
# EMA12+EMA23: 0.68
# EMA12+EMA25: 0.63
# EMA12+EMA27: 0.64
# EMA12+EMA29: 0.59
# EMA12+EMA31: 0.64
# EMA13+EMA14: 0.57
# EMA13+EMA16: 0.54
# EMA13+EMA18: 0.56
# EMA13+EMA20: 0.57
# EMA13+EMA22: 0.64
# EMA13+EMA24: 0.66
# EMA13+EMA26: 0.63
# EMA13+EMA28: 0.63
# EMA13+EMA30: 0.62
# EMA13+EMA32: 0.59
# EMA14+EMA15: 0.50
# EMA14+EMA17: 0.61
# EMA14+EMA19: 0.58
# EMA14+EMA21: 0.63
# EMA14+EMA25: 0.59
# EMA14+EMA23: 0.57
# EMA14+EMA27: 0.63
# EMA14+EMA29: 0.59
# EMA14+EMA31: 0.60
# EMA14+EMA33: 0.60
# EMA15+EMA16: 0.45
# EMA15+EMA18: 0.54
# EMA15+EMA20: 0.62
# EMA15+EMA22: 0.55
# EMA15+EMA24: 0.58
# EMA15+EMA26: 0.59
# EMA15+EMA28: 0.61
# EMA15+EMA30: 0.60
# EMA15+EMA34: 0.52
# EMA15+EMA32: 0.60
# EMA16+EMA17: 0.53
# EMA16+EMA19: 0.49
# EMA16+EMA21: 0.56
# EMA16+EMA23: 0.53
# EMA16+EMA25: 0.57
# EMA16+EMA27: 0.59
# EMA16+EMA29: 0.54
# EMA16+EMA31: 0.60
# EMA16+EMA35: 0.51
# EMA16+EMA33: 0.54
# EMA17+EMA18: 0.47
# EMA17+EMA20: 0.52
# EMA17+EMA22: 0.50
# EMA17+EMA24: 0.58
# EMA17+EMA26: 0.60
# EMA17+EMA28: 0.59
# EMA17+EMA30: 0.54
# EMA17+EMA32: 0.55
# EMA17+EMA34: 0.52
# EMA17+EMA36: 0.51
# EMA18+EMA19: 0.29
# EMA18+EMA21: 0.56
# EMA18+EMA23: 0.48
# EMA18+EMA25: 0.56
# EMA18+EMA27: 0.53
# EMA18+EMA29: 0.49
# EMA18+EMA31: 0.51
# EMA18+EMA35: 0.51
# EMA18+EMA33: 0.50
# EMA18+EMA37: 0.51
# EMA19+EMA20: 0.67
# EMA19+EMA22: 0.54
# EMA19+EMA26: 0.52
# EMA19+EMA24: 0.56
# EMA19+EMA28: 0.55
# EMA19+EMA30: 0.52
# EMA19+EMA32: 0.48
# EMA19+EMA34: 0.53
# EMA19+EMA36: 0.55
# EMA19+EMA38: 0.46