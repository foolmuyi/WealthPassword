# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import aiohttp, asyncio
import logging
from fake_useragent import UserAgent
import re,time



def getCodeDcit():
	# headers= {'User-Agent':str(UserAgent(use_cache_server=False, verify_ssl=False).random)}
	url = 'http://fund.eastmoney.com/js/fundcode_search.js'
	res = requests.get(url)
	pattern = r'\[\[.*\]\]'
	match_res = re.findall(pattern, res.text)
	fund_list = json.loads(match_res[0])  # 字符串列表的每一个元素也是列表，json解析
	fund_dict = {fund[0]:fund[2] for fund in fund_list}
	return fund_dict


def getOneFund(code):
	url = 'http://fund.eastmoney.com/pingzhongdata/'+code+'.js'
	res = requests.get(url)
	# print(res.text)
	pattern = r'(?<=Data_ACWorthTrend\s\=\s).*?(?=\;)'  # .*?的?表示非贪婪匹配
	match_res = re.findall(pattern, res.text)
	acc_worth_trend = json.loads(match_res[0])  # 累计净值（accumulated worth）走势
	# 除以1000是因为天天基金API返回的时间戳有13位且后三位均为0
	worth_trend_dict = {time.strftime('%Y%m%d', time.localtime(each[0]/1000)):each[1] for each in acc_worth_trend}
	return worth_trend_dict




worth_trend = getOneFund('001606')
# allCode = getCodeDcit()

async def writeOneFund(fund_data, code):
	global write_count, fundNum
	print('Writing data of '+code+'      '+str(write_count)+'/'+str(fundNum))
	fund_data.to_csv('../../Data/'+code+'.csv', index=False)


async def dlAllFund():
	global fundNum
	code_list = getAllCode()
	# code_list = code_list[:500]
	print('Download start!')
	fundNum = len(code_list)
	tasks = [asyncio.create_task(dlOneFund(code)) for code in code_list]
	await asyncio.gather(*tasks)

# asyncio.run(dlAllFund())
