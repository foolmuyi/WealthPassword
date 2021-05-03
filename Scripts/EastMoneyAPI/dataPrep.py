# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import aiohttp, asyncio
import datetime as dt
from fake_useragent import UserAgent
import re,time,js2py,logging
from tenacity import *


# 日志配置
logging.basicConfig(filename='../log/'+dt.datetime.today().strftime("%y%m%d")+'.log',level=logging.INFO,format='%(asctime)s:%(levelname)s:%(message)s')


# 获取所有基金代码
def getCodeList():
	print('Getting fund list.......')
	# headers= {'User-Agent':str(UserAgent(use_cache_server=False, verify_ssl=False).random)}
	url = 'http://fund.eastmoney.com/js/fundcode_search.js'
	res = requests.get(url)
	context = js2py.EvalJs()  # 用js2py代替正则表达式定位JavaScript变量
	context.execute(res.text)
	fund_list = context.r.to_list()
	return fund_list


# 将基金数据写入csv文件
def write2file(code,df_acc_worth_trend):
	print('Writting data of '+code)
	df_acc_worth_trend.to_csv('../../Data/'+code+'.csv', index=False)


# 填充缺失值
def fillMissingValues(raw_list):
	try:
		raw_list_full = [raw_list[i] if raw_list[i][1] != None else [raw_list[i][0],(raw_list[i-1][1]+raw_list[i+1][1])/2] for i in range(len(raw_list))]    # 以前后值平均值填充
		print('Fill in missing values with the average of the prior value and the next value')
	except:
		try:
			raw_list_full = [raw_list[i] if raw_list[i][1] != None else [raw_list[i][0],raw_list[i-1][1]] for i in range(len(raw_list))]    # 若发生异常，以前值填充
			print('Error occurred! Fill in missing values with the prior value')
		except:
			try:
				raw_list_full = [raw_list[i] if raw_list[i][1] != None else [raw_list[i][0],raw_list[i+1][1]] for i in range(len(raw_list))]    # 若继续异常，以后值填充
				print('Error occurred! Fill in missing values with the next value')
			except:
				raw_list_full = [raw_list[i] if raw_list[i][1] != None else [raw_list[i][0],0] for i in range(len(raw_list))]    # 若还是异常，以0填充
				print('Error occurred! Fill in missing values with 0')
	return raw_list_full


@retry(stop=stop_after_attempt(5),wait=wait_random(min=1,max=3),retry=retry_if_exception_type(requests.exceptions.ChunkedEncodingError))
def getOneFund(code):
	print('Downloading data of '+code)
	try:
		url = 'http://fund.eastmoney.com/pingzhongdata/'+code+'.js'
		res = requests.get(url)
		context = js2py.EvalJs()
		context.execute(res.text)
		raw_list = context.Data_ACWorthTrend.to_list()    # 原始累计净值走势，时间为时间戳格式
		if None in [each[1] for each in raw_list]:    # 检查是否有缺失值
			raw_list_full = fillMissingValues(raw_list)
		else:
			raw_list_full = raw_list
		change_list = [round(((raw_list_full[i][1]-raw_list_full[i-1][1])/raw_list_full[i-1][1])*100,2) if i != 0 else 0 for i in range(len(raw_list_full))]    # 计算每日涨跌幅
		acc_worth_trend = [[time.strftime('%Y%m%d', time.localtime(raw_list_full[i][0]/1000)),raw_list_full[i][1],change_list[i]] for i in range(len(raw_list_full))]    # 构造[日期，净值，当日涨跌幅]格式数据
		df_acc_worth_trend = pd.DataFrame(acc_worth_trend)
		df_acc_worth_trend.columns = ['Date','AccWorth','Change']
		write2file(code, df_acc_worth_trend)
	except js2py.internals.simplex.JsException as e:
		print('------------------------------------')
		print('Page not found: '+code)
		print(e)
		print('------------------------------------')
		logging.error(code)
		logging.error(e)
	# else:
	# 	print('Other Exceptions')
	# 	logging.error(code)
	# 	logging.error(Exception)



# getOneFund('000005')
allCode = getCodeList()
for each in allCode:
	getOneFund(each[0])




# async def writeOneFund(fund_data, code):
# 	# global write_count, fundNum
# 	print('Writing data of '+code+'      '+str(write_count)+'/'+str(fundNum))
# 	fund_data.to_csv('../../Data/'+code+'.csv', index=False)


# async def dlAllFund():
# 	global fundNum
# 	code_list = getAllCode()
# 	# code_list = code_list[:500]
# 	print('Download start!')
# 	fundNum = len(code_list)
# 	tasks = [asyncio.create_task(dlOneFund(code)) for code in code_list]
# 	await asyncio.gather(*tasks)

# asyncio.run(dlAllFund())
