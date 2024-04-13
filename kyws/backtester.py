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
		# print('Total balance: '+str(self.balance+self.myShares*self.accWorth_series[str(self.today)]))
		# print('Total ratio of return: '+str(round(((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000,2)))
		try:
			r_ratio = round(((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000,2)
			return r_ratio
		except:
			return 0


code_list = ['515880','512580','159928','512800','512170','512690','159944','512660','159870','515220',
'515210','515170','512760','512400','513050','515030','510300','510050','515790','159949']
start_date = datetime.date(2019,9,3)
end_date = datetime.date(2021,7,1)
fast_param = 12
slow_param = 21

# fund_code = '512690'
# tester1 = Backtester(fund_code,start_date,end_date)
# tester1.test(12,21)
# tester1.show_plot(12,21)

def run(code_list,start_date,end_date,fast_param,slow_param):
	ratio_avg = 0
	total_num = len(code_list)
	for fund_code in code_list:
		try:
			tester1 = Backtester(fund_code,start_date,end_date)
			ratio_avg += tester1.test(fast_param,slow_param)
		except Exception as e:
			print(fund_code+'    '+str(e))
			total_num -= 1
	ratio_avg = ratio_avg/total_num
	print('{}{}+{}{}: {:.2f}'.format('EMA',fast_param,'EMA',slow_param,ratio_avg))

run(code_list,start_date,end_date,fast_param,slow_param)

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