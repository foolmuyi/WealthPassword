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
			print('Buy '+str(self.balance)+' on '+str(tomo))
			self.balance = 0
			self.buy_date.append(tomo)

	def Sell(self):
		if self.myShares > 0:
			tomo,tomo_accWorth = self.getTomoPrice()
			sell_amount = round(self.myShares*tomo_accWorth*0.995,2)    # 粗略假设手续费0.5%
			sell_amount = round(self.myShares*tomo_accWorth,2)
			self.balance += sell_amount
			print('Sell '+str(sell_amount)+' on '+str(tomo))
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


# fund_code = '004789'
code_list = ['005969','006253','007193','501058','006448','004235','007995','008764','002360','005856','004533','004041']
start_date = datetime.date(2019,6,10)
end_date = datetime.date(2021,7,1)

fund_code = '006327'
tester1 = Backtester(fund_code,start_date,end_date)
tester1.test(12,14)
tester1.show_plot(12,14)

# for fast_param in range(2,3):
# 	for slow_param in range(3,20):
# 		ratio_avg = 0
# 		for fund_code in code_list:
# 			tester1 = Backtester(fund_code,start_date,end_date)
# 			ratio_avg += tester1.test(fast_param,slow_param)
# 		ratio_avg = ratio_avg/len(code_list)
# 		print('{}{}+{}{}: {:.2f}'.format('EMA',fast_param,'EMA',slow_param,ratio_avg))

# # tester1.show_plot()

# ratio_ref = 0
# for fund_code in code_list:
# 	file_path = '../Data/'+fund_code+'.csv'
# 	df = pd.read_csv(file_path)
# 	df['Date'] = pd.to_datetime(df['Date'])
# 	df = df.set_index('Date')
# 	accWorth_series = pd.Series(df['AccWorth'], index=df.index)
# 	ratio_ref += (accWorth_series[str(end_date)]-accWorth_series[str(start_date)])/accWorth_series[str(start_date)]
# print('{}: {:.2f}'.format('ref',ratio_ref/len(code_list)))



# ['001984', '001915', '005689', '001717', '005176', '000727', '004851', '001508', '005303', '001766', '001510', '005304', '003230', '002264', 
# '003231', '002770', '002771', '001171', '004075', '050026', '161219', '161726', '213001', '000924', '000220', '001558', '002408', '005112', 
# '519026', '001559', '000977', '000339', '002446', '001069', '005520', '000831', '003095', '002124', '240020', '003096', '005805', '001864', 
# '002708', '161616', '460005', '006113', '001645', '000523', '004905', '161035', '006228', '005760', '001538', '003291', '110023', '206009', 
# '200012', '000452', '519773', '000960', '005825', '001815', '006229', '470006', '002082', '001388', '501009', '512290', '003032', '501010', 
# '020010', '000020', '001822', '002780', '121006', '006756', '001387', '320012', '005738', '007043', '002213', '005726', '001218', '002300', 
# '006757', '501005', '006240', '161727', '005911', '501006', '001861', '006881', '000362', '002340', '001182', '240001', '003581', '006241', '005671', '002980']