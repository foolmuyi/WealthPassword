# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import aiohttp, asyncio
import logging


token = ""

def getAllCode():
	print('Getting fund code list..........')
	url = 'https://api.doctorxiong.club/v1/fund/all'
	res = requests.get(url)
	data = json.loads(res.text)['data']
	code_list = []
	for each in data:
		if each[3] in ['混合型','股票型','股票指数','QDII-指数','QDII-ETF','QDII','联接基金']:
			code_list.append(each[0])
	return code_list

download_count = 1
write_count = 1
fundNum = 0
run_count = 0

async def writeOneFund(fund_data, code):
	global write_count, fundNum
	print('Writing data of '+code+'      '+str(write_count)+'/'+str(fundNum))
	fund_data.to_csv('../../Data/'+code+'.csv', index=False)

async def dlOneFund(code):
	global download_count,write_count,fundNum,run_count
	fund_detail_url = 'https://api.doctorxiong.club/v1/fund/detail?code='
	headers = {'Content-Type': 'application/json', 'token': token}
	connector = aiohttp.TCPConnector(limit=30, verify_ssl=False)
	async with aiohttp.ClientSession(connector=connector) as session:
		try:
			async with session.get(fund_detail_url+code, headers=headers, timeout=0) as res:
				print('Downloading data of '+code+'      '+str(download_count)+'/'+str(fundNum))
				download_count += 1
				data = await res.json()
				netWorth = data['data']['netWorthData']
				df_netWorth = pd.DataFrame(netWorth)
				df_netWorth.columns = ['Date','netWorth','Change','Bonus']
				await writeOneFund(df_netWorth, code)
		except Exception as e:
			logging.exception(e)
			print('ohnoooooooooooooooooooooooooooooooooooooooooooooooooooooooooo        '+code)
			# print(await res.text())
			pass
		finally:
			write_count += 1
	await session.close()

async def dlAllFund():
	global fundNum
	code_list = getAllCode()
	# code_list = code_list[:500]
	print('Download start!')
	fundNum = len(code_list)
	tasks = [asyncio.create_task(dlOneFund(code)) for code in code_list]
	await asyncio.gather(*tasks)

asyncio.run(dlAllFund())
