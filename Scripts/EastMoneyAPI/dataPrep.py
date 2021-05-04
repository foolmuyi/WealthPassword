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


# 获取所有基金代码
@retry(stop=stop_after_attempt(5),wait=wait_random(min=1,max=3),retry=retry_if_exception_type(requests.exceptions.ChunkedEncodingError))
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


# 日志配置
logging.basicConfig(filename='../log/'+dt.datetime.today().strftime("%y%m%d")+'.log',level=logging.INFO,format='%(asctime)s:%(levelname)s:%(message)s')
# 报错信息处理（格式化输出并写入日志）
def printExceptions(code,e):
	excp_type = str(e).split(':')[0]
	# excp_type = excp_info[0]
	print('\n')
	print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
	if excp_type == 'SyntaxError':
		print('Page not found: '+code)
	elif excp_type == 'ReferenceError':
		print('Special fund type: '+code)
	elif excp_type == 'Length mismatch':
		print('No accumulated worth trend data found: '+code)
	else:
		print('New error type: '+code+'!!!!!')
		print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
		logging.error(code)
		logging.error(e)
		raise    # 若有其他类型异常（一般是网络连接异常），抛出，触发getOneFund函数的自动重试条件
	print(e)
	print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
	print('\n')
	logging.error(code)
	logging.error(e)


@retry(stop=stop_after_attempt(5),wait=wait_random(min=1,max=3))
def getOneFund(code):
	print('Downloading data of '+code)
	try:
		url = 'http://fund.eastmoney.com/pingzhongdata/'+code+'.js'
		try:
			res = requests.get(url)
		except:
			raise
		context = js2py.EvalJs()
		context.execute(res.text)
		raw_list = context.Data_ACWorthTrend.to_list()    # 原始累计净值走势，时间为时间戳格式
		raw_list_full = raw_list
		while None in [each[1] for each in raw_list_full]:    # 检查是否有缺失值，考虑到连续多个缺失值的情况，用while循环多次调用填充缺失值函数，直到没有缺失值
			raw_list_full = fillMissingValues(raw_list_full)
		change_list = [round(((raw_list_full[i][1]-raw_list_full[i-1][1])/raw_list_full[i-1][1])*100,2) if i != 0 else 0 for i in range(len(raw_list_full))]    # 计算每日涨跌幅
		acc_worth_trend = [[time.strftime('%Y%m%d', time.localtime(raw_list_full[i][0]/1000)),raw_list_full[i][1],change_list[i]] for i in range(len(raw_list_full))]    # 构造[日期，净值，当日涨跌幅]格式数据
		df_acc_worth_trend = pd.DataFrame(acc_worth_trend)
		try:
			df_acc_worth_trend.columns = ['Date','AccWorth','Change']
		except Exception as e:
			printExceptions(code,e)
			return
		write2file(code, df_acc_worth_trend)
	except Exception as e:
		printExceptions(code,e)



# getOneFund('000111')
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
