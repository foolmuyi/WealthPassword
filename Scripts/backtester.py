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
		# return df['Change'].values.tolist()

	def Buy(self):
		if self.balance > 0:
			today_accWorth = self.accWorth_series[str(self.today)]
			self.myShares += self.balance/today_accWorth
			print('Buy '+str(self.balance)+' on '+str(self.today))
			self.balance = 0
			self.buy_date.append(self.today)

	def Sell(self):
		if self.myShares > 0:
			today_accWorth = self.accWorth_series[str(self.today)]
			self.balance += self.myShares*today_accWorth
			print('Sell '+str(self.myShares*today_accWorth)+' on '+str(self.today))
			self.myShares = 0
			self.sell_date.append(self.today)

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
		print('Total ratio of return: '+str(((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000))
		try:
			r_ratio = ((self.balance+self.myShares*self.accWorth_series[str(self.today)])-5000)/5000
			return r_ratio
		except:
			return 0


fund_code = '002190'
start_date = datetime.date(2020,1,2)
end_date = datetime.date(2021,5,21)
tester1 = backTester(fund_code,start_date,end_date)
tester1.test()
tester1.show_plot()
# dailyChange = tester1.readFile()
# print(am.sharpeRatio(dailyChange))



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
# print(min(accWorth_series))
