# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d
import alchemist as am


class backTester(object):
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
			print('Buy '+str(self.balance)+' on '+str(tomo))
			self.balance = 0
			self.buy_date.append(tomo)

	def Sell(self):
		if self.myShares > 0:
			tomo,tomo_accWorth = self.getTomoPrice()
			sell_amount = round(self.myShares*tomo_accWorth*0.995,2)    # 粗略假设手续费0.5%
			self.balance += sell_amount    # 粗略假设手续费0.5%
			print('Sell '+str(sell_amount)+' on '+str(tomo))
			self.myShares = 0
			self.sell_date.append(tomo)

	def show_plot(self):
		self.accWorth_series.plot()
		plt.vlines(self.buy_date,min(self.accWorth_series),max(self.accWorth_series),color='g')
		plt.vlines(self.sell_date,min(self.accWorth_series),max(self.accWorth_series),color='r')
		plt.show()

	def test(self):
		self.readFile()
		for i in range((self.end_date-self.start_date).days):
			self.today = self.start_date+datetime.timedelta(days=i)
			signal = am.getSignal(self.fund_code,self.today)
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


fund_code = '002190'
start_date = datetime.date(2018,5,21)
end_date = datetime.date(2021,5,21)
tester1 = backTester(fund_code,start_date,end_date)
tester1.test()
tester1.show_plot()



# fund_code_list = []
# data_dir = '../Data'
# file_list = os.listdir(data_dir)
# for each in file_list:
# 	fund_code_list.append(each[:6])
# for fund_code in fund_code_list:
# 	start_date = datetime.date(2020,1,2)
# 	end_date = datetime.date(2020,12,31)
# 	tester1 = backTester(fund_code,start_date,end_date)
# 	return_ratio = tester1.test()
# 	if return_ratio > 0.5:
# 		print(fund_code+' : '+str(return_ratio))



# fund_code = '320007'
# file_path = '../Data/'+fund_code+'.csv'
# df = pd.read_csv(file_path)
# df['Date'] = pd.to_datetime(df['Date'])
# df = df.set_index('Date')
# accWorth_series = pd.Series(df['AccWorth'], index=df.index)
# print(accWorth_series['2020-07-10'])
# print(accWorth_series['2020-07-13'])
# print(str(accWorth_series.index[len(accWorth_series[:'2020-07-10'])]).split(' ')[0])
