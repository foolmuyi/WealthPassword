# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d
import alchemist as am


class backTester(object):
	def __init__(self):
		self.balance = 5000
		self.myShares = 0
		self.buy_date = []
		self.sell_date = []

	def Buy(self,accWorth,end_date,i):
		if self.balance > 0:
			self.myShares += self.balance/accWorth[-1]
			print('Buy '+str(self.balance)+' on '+str(end_date))
			self.balance = 0
			self.buy_date.append(i)

	def Sell(self,accWorth,end_date,i):
		if self.myShares > 0:
			self.balance += self.myShares*accWorth[-1]
			print('Sell '+str(self.myShares*accWorth[-1])+' on '+str(end_date))
			self.myShares = 0
			self.sell_date.append(i)

	def show_plot(self,accWorth):
		plt.plot(accWorth)
		plt.vlines(self.buy_date,1.5,3.5,color='g')
		plt.vlines(self.sell_date,1.5,3.5,color='r')
		plt.legend()
		plt.show()


tester1 = backTester()
start_date = dt.date(2019,1,2)
for i in range(365,730):
	end_date = start_date+dt.timedelta(days=i)
	signal,accWorth = am.getSignal('320007',start_date,end_date)
	if signal == 'Buy':
		tester1.Buy(accWorth,end_date,i)
	elif signal == 'Sell':
		tester1.Sell(accWorth,end_date,i)

tester1.show_plot(accWorth)