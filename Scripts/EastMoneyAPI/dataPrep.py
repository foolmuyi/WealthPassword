# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import aiohttp, asyncio
import datetime as dt
import re,time,logging,js2py
from tenacity import *


class DataCollector(object):
	def __init__(self):
		self.fund_num = 0    # 基金总数
		self.completed_num = 0    # 已完成的基金个数


	# 获取所有基金代码
	@retry(stop=stop_after_attempt(5),wait=wait_random(min=1,max=3),retry=retry_if_exception_type(requests.exceptions.ChunkedEncodingError))
	def getCodeList(self):
		print('Getting fund list.......')
		url = 'http://fund.eastmoney.com/js/fundcode_search.js'
		res = requests.get(url)
		context = js2py.EvalJs()  # 用js2py代替正则表达式定位JavaScript变量
		context.execute(res.text)
		fund_list = context.r.to_list()
		return fund_list


	# 将基金数据写入csv文件
	async def write2file(self,code,df_acc_worth_trend):
		print('Writting data of '+code+'          '+str(self.completed_num+1)+'/'+str(self.fund_num))
		df_acc_worth_trend.to_csv('../../Data/'+code+'.csv', index=False)
		self.completed_num += 1


	# 填充缺失值
	async def fillMissingValues(self,raw_list):
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
	async def printExceptions(self,fund_code,status_code,e):
		print('\n')
		print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
		if status_code == 200:
			excp_type = str(e).split(':')[0]
			if excp_type == 'list index out of range':
				error_msg = 'Special fund type: '+fund_code
				print(error_msg)
				logging.error(error_msg)
				self.completed_num += 1
			elif excp_type == 'Length mismatch':
				error_msg = 'No accumulated worth trend data found: '+fund_code
				print(error_msg)
				logging.error(error_msg)
				self.completed_num += 1
			else:
				print('New error type: '+fund_code+'!!!!!')
				print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
				logging.error(fund_code)
				logging.error(excp_type)
				logging.error(e)
				raise    # 若有其他类型异常（一般是网络连接异常），抛出，触发getOneFund函数的自动重试条件
		elif status_code == 404:
			error_msg = 'Page not found: '+fund_code
			print(error_msg)
			logging.error(error_msg)
			self.completed_num += 1
		else:
			print('New status code: '+str(status_code))
			logging.error(fund_code)
			logging.error(status_code)
			logging.error(e)
		print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
		print('\n')


	# 协程版
	@retry(stop=stop_after_attempt(5),wait=wait_random(min=1,max=3))
	async def getOneFund(self,fund_code):
		print('Downloading data of '+fund_code)
		try:
			url = 'http://fund.eastmoney.com/pingzhongdata/'+fund_code+'.js'
			connector = aiohttp.TCPConnector(limit=50, ssl=False)
			try:
				async with aiohttp.ClientSession(connector=connector) as session:
					async with session.get(url, timeout=0) as resp:
						res = await resp.text()
						status_code = resp.status
			except:
				raise
			## js2py执行时间太长，且不支持协程，弃用。正则表达式虽然不如js2py看起来优雅，但执行速度快
			pattern = r'(?<=Data_ACWorthTrend\s\=\s).*?(?=\;)'  # .*?的?表示非贪婪匹配
			match_res = re.findall(pattern,res)
			try:
				raw_list = json.loads(match_res[0])  # 累计净值（accumulated worth）走势
			except Exception as e:
				await self.printExceptions(fund_code,status_code,e)
				self.completed_num += 1
				return
			raw_list_full = raw_list
			while None in [each[1] for each in raw_list_full]:    # 检查是否有缺失值，考虑到连续多个缺失值的情况，用while循环多次调用填充缺失值函数，直到没有缺失值
				raw_list_full = await self.fillMissingValues(raw_list_full)
			change_list = [round(((raw_list_full[i][1]-raw_list_full[i-1][1])/raw_list_full[i-1][1])*100,2) if i != 0 else 0 for i in range(len(raw_list_full))]    # 计算每日涨跌幅
			acc_worth_trend = [[time.strftime('%Y%m%d', time.localtime(raw_list_full[i][0]/1000)),raw_list_full[i][1],change_list[i]] for i in range(len(raw_list_full))]    # 构造[日期，净值，当日涨跌幅]格式数据
			df_acc_worth_trend = pd.DataFrame(acc_worth_trend)
			try:
				df_acc_worth_trend.columns = ['Date','AccWorth','Change']
			except Exception as e:
				await self.printExceptions(fund_code,status_code,e)
				self.completed_num += 1
				return
			await self.write2file(fund_code, df_acc_worth_trend)
		except Exception as e:
			await self.printExceptions(fund_code,status_code,e)


	# 分批下载，一批100支基金
	async def dl100Fund(self,fund_list):
		tasks = [asyncio.create_task(self.getOneFund(each[0])) for each in fund_list]
		await asyncio.gather(*tasks)


	async def dlAllFund(self):
		all_fund = self.getCodeList()
		# all_fund = all_fund[:233]
		self.fund_num = len(all_fund)
		for i in range(self.fund_num//100):
			fund_list = all_fund[i*100:min((i+1)*100,self.fund_num+1)]
			await self.dl100Fund(fund_list)

collector = DataCollector()
asyncio.run(collector.dlAllFund())