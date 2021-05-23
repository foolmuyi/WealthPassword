# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def sharpeRatio(accWorth,dailyChange):
	return ((accWorth[-1]-accWorth[0])/accWorth[-1])/np.var(dailyChange)

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


df = pd.read_csv('../Data/002943.csv')
accWorth = df['AccWorth'].values.tolist()[-250:]
dailyChange = df['Change'].values.tolist()[-250:]
ma5 = ma(accWorth,period=5,weights=[1,2,3,4,5])
ma10 = ma(accWorth,period=10,weights=[1,2,3,4,5,6,7,8,9,10])
fft_ma5 = np.fft.fft(accWorth)
filter_ma5 = np.where(np.abs(fft_ma5)<7,0,fft_ma5)
new_ma5 = np.real(np.fft.ifft(filter_ma5))
slope = np.diff(new_ma5).tolist()
slope[0:5] = [1.5,1.5,1.5,1.5,1.5]
slope[-5:] = [1.5,1.5,1.5,1.5,1.5]
buy_spots = []
sell_spots = []
for i in range(len(slope)):
	if slope[i-1]>=0 and slope[i]<0:
		sell_spots.append(i)
	elif slope[i-1]<=0 and slope[i]>0:
		buy_spots.append(i)




plt.plot(accWorth,label='Acc Worth')
plt.plot(ma5,label='MA5')
plt.plot(ma10,label='MA10')
# plt.plot(new_ma5,label='New MA5')
# plt.vlines(buy_spots,1.5,3.25,color='g')
# plt.vlines(sell_spots,1.5,3.25,color='r')
plt.legend()
plt.show()