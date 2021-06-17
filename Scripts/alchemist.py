# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os,requests,json
import time,datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


import sys   
sys.setrecursionlimit(100000)


# 计算夏普比率
def sharpeRatio(dailyChange):
	dailyChange = [each/100 for each in dailyChange]
	if (len(dailyChange) == 0) or (np.std(dailyChange) == 0):
		sharpe_ratio = 0
	else:
		sharpe_ratio = np.mean(dailyChange)/np.std(dailyChange)*np.sqrt(252)
	return sharpe_ratio

# 计算均值，默认五日算数均值
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



# def ema(data,period):
# 	(2*data[-1]+(period-1)*ema(data[:k-1],period)[-1])/(period+1)



# 通过几只典型基金来计算所选时间段内开市天数
def days_counter(data_dir,start_date,end_date):
	test_fund_list = ['320007','000083','163406']    # 典型基金列表
	days_sum = 0
	try:
		for each in test_fund_list:
			file_path = data_dir+'/'+each+'.csv'
			if os.path.exists(file_path):
				df = pd.read_csv(file_path)
				df['Date'] = pd.to_datetime(df['Date'])
				df = df.set_index('Date')
				df = df[start_date:end_date]
				days_sum += df.shape[0]
			else:
				test_fund_list.remove(each)    # 若不存在则不考虑
	except Exception as e:
		pass
	return days_sum/len(test_fund_list)

# 按夏普比率进行筛选
def filter_by_sharpe(data_dir, start_date='2021', end_date=None, top=100):
	sharpe_ratio_list = {}
	total_days = days_counter(data_dir,start_date,end_date)
	file_list = os.listdir(data_dir)
	for each in file_list:
		file_path = os.path.join(data_dir,each)
		df = pd.read_csv(file_path)
		try:
			df['Date'] = pd.to_datetime(df['Date'])
			df = df.set_index('Date')
			df = df[start_date:end_date]
			accWorth = df['AccWorth'].values.tolist()
			dailyChange = df['Change'].values.tolist()
			if len(dailyChange) < total_days-5:    # 去除成立时间太短和按周公布净值的基金(减5是为了留有一定的裕度)
				sharpe_ratio = 0
			else:
				sharpe_ratio = sharpeRatio(dailyChange)
			if (accWorth[-1]-accWorth[0])/accWorth[0] >= total_days/1000:    # 去掉收益率太低的基金
				sharpe_ratio_list[each[:6]] = sharpe_ratio
		except Exception as e:
			pass
	result = sorted(sharpe_ratio_list.items(), key = lambda x:x[1], reverse=True)[:top]    # 取前top名
	return result

# 示例：筛选2021年至今和2020整年夏普比率均为前100的基金
# data_dir = '../Data'
# half_year = filter_by_sharpe(data_dir,'2021')
# half_year_code = [each[0] for each in half_year]
# print(half_year)
# one_year = filter_by_sharpe(data_dir,'2020-01','2020-12')
# one_year_code = [each[0] for each in one_year]
# print('\n')
# print(one_year)
# print('\n')
# print(list(set(half_year_code).intersection(set(one_year_code))))


def getSignal(fund_code,test_date=None):
	file_path = '../Data/'+fund_code+'.csv'
	df = pd.read_csv(file_path)
	df['Date'] = pd.to_datetime(df['Date'])
	df = df.set_index('Date')
	df = df['2019':test_date]    # 为减少运算量，暂时取2019年以后的数据
	accWorth = df['AccWorth'].values.tolist()
	dailyChange = df['Change'].values.tolist()
	try:
		ma5 = ma(accWorth,period=5,weights=[1,2,3,5,8])
	except Exception as e:
		return -1
	new_ma5 = ma(ma5,period=5,weights=[1,2,3,5,8])
	# plt.plot(accWorth,label='accWorth')
	# plt.plot(ma5,label='MA5')
	# # plt.plot(new_ma5,label='New MA5')
	# plt.legend()
	# plt.show()
	slope = np.diff(new_ma5).tolist()
	# plt.plot(slope)
	# # plt.scatter([i for i in range(len(slope))],slope)
	# plt.hlines([-0.02],1,500,'r')
	# plt.show()
	if slope[-1]>0:
		return 'Buy'
	elif slope[-1]<=0:
		return 'Sell'
	else:
		return 'Hold'

url= 'https://api.doctorxiong.club/v1/stock/kline/day?code=sh000001&startDate=2000-09-01&type=1'
res = requests.get(url)
data = json.loads(res.text)['data']
close_price = [float(each[2]) for each in data]
print(ema(close_price,144))


# test_date = datetime.date(2020,12,31)
# getSignal('002190',test_date)

# plt.plot(accWorth,label='Acc Worth')
# plt.plot(ma5,label='MA5')
# plt.plot(new_ma5,label='New MA5')
# # plt.plot(ma10,label='MA10')
# # plt.plot(new_ma5,label='New MA5')
# plt.vlines(buy_spots,min(accWorth),max(accWorth),color='g')
# plt.vlines(sell_spots,min(accWorth),max(accWorth),color='r')
# plt.legend()
# plt.show()