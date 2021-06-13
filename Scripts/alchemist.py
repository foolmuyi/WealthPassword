# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# 计算夏普比率
def sharpeRatio(dailyChange):
	dailyChange = [each/100 for each in dailyChange]
	if (len(dailyChange) == 0) or (np.std(dailyChange) == 0):
		sharpe_ratio = 0
	else:
		sharpe_ratio = np.mean(dailyChange)/np.std(dailyChange)*np.sqrt(252)
	return sharpe_ratio

# 计算均值，默认五日算数均值
# def ma(data,period=5,weights='default'):
# 	if period <= 0:
# 		raise IndexError('Period is '+str(period)+', which is less than 1')
# 	elif len(data) < period:
# 		raise IndexError('Cannot obtain MA because the length of the list is '+str(len(data))+' while the period is '+str(period))
# 	elif (weights != 'default' and len(weights) != period):
# 		raise IndexError('The length of weight list is '+str(len(weights))+' while the period is '+str(period))
# 	else:
# 		weights = [1 for _ in range(period)] if weights=='default' else weights
# 		ma_list = [data[i] if i<period-1 else np.sum(np.array(data[i-period+1:i+1])*np.array(weights))/np.sum(weights) for i in range(len(data))]
# 		return ma_list

# 按夏普比率进行筛选
def filter_by_sharpe(data_dir, period=126, top=100):
	sharpe_ratio_list = {}
	file_list = os.listdir(data_dir)
	for each in file_list:
		file_path = os.path.join(data_dir,each)
		df = pd.read_csv(file_path)
		try:
			df = df[-period:]
			accWorth = df['AccWorth'].values.tolist()
			dailyChange = df['Change'].values.tolist()
			sharpe_ratio = sharpeRatio(dailyChange)
			if (accWorth[-1]-accWorth[0])/accWorth[0] >= period/1000:    # 去掉收益率太低的基金
				sharpe_ratio_list[each[:6]] = sharpe_ratio
		except Exception as e:
			pass
	result = sorted(sharpe_ratio_list.items(), key = lambda x:x[1], reverse=True)[:top]    # 取前top名
	return result

data_dir = '../Data'
half_year = filter_by_sharpe(data_dir)
half_year_code = [each[0] for each in half_year]
print(half_year)
one_year = filter_by_sharpe(data_dir,252)
one_year_code = [each[0] for each in one_year]
print('\n')
print(one_year)
print('\n')
print(list(set(half_year_code).intersection(set(one_year_code))))


'''
[('002149', 4.500442811169699), ('008099', 3.617632834975259), ('006448', 3.4437561927369074), ('001763', 3.3723080989059575), 
('002943', 3.2185678333767105), ('001487', 3.11227566169346), ('005233', 3.0547716359310564), ('001681', 2.996398914095422),  
('004235', 2.923452365633849), ('161222', 2.764638117278396), ('005613', 2.7406551935715937),
('000049', 2.5938070073335213), ('162411', 2.5902233611914847), 
('008763', 2.589581350083412), ('007844', 2.584233817715173), ('008764', 2.5827693621003336), ('005561', 2.5657550065240735), 
('005562', 2.5593437939839494), ('007994', 2.5593163506610783), ('007995', 2.536153911086817), ('159980', 2.52522636788386), 
('160416', 2.4993769986150633), ('160140', 2.483543917056399)]
'''


# df = pd.read_csv('../Data/001316.csv')
# dailyChange = df['Change'].values.tolist()[-250:]
# ma5 = ma(accWorth,period=5,weights=[1,2,3,4,5])
# ma10 = ma(accWorth,period=10,weights=[1,2,3,4,5,6,7,8,9,10])
# fft_ma5 = np.fft.fft(accWorth)
# filter_ma5 = np.where(np.abs(fft_ma5)<7,0,fft_ma5)
# new_ma5 = np.real(np.fft.ifft(filter_ma5))
# slope = np.diff(new_ma5).tolist()
# slope[0:5] = [1.5,1.5,1.5,1.5,1.5]
# slope[-5:] = [1.5,1.5,1.5,1.5,1.5]
# buy_spots = []
# sell_spots = []
# for i in range(len(slope)):
# 	if slope[i-1]>=0 and slope[i]<0:
# 		sell_spots.append(i)
# 	elif slope[i-1]<=0 and slope[i]>0:
# 		buy_spots.append(i)




# plt.plot(accWorth,label='Acc Worth')
# # plt.plot(ma5,label='MA5')
# # plt.plot(ma10,label='MA10')
# # plt.plot(new_ma5,label='New MA5')
# plt.vlines(buy_spots,1.5,3.25,color='g')
# plt.vlines(sell_spots,1.5,3.25,color='r')
# plt.legend()
# plt.show()