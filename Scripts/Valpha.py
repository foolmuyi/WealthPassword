# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests,json,os,time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d
import aiohttp, asyncio
import logging


# 下载数据
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
	fund_data.to_csv('./fundData/'+code+'.csv', index=False)

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
			logging.basicConfig(level=logging.DEBUG,
                    filename='0424.log',
                    filemode='a',
                    format=
                    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    #日志格式
                    )
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

# asyncio.run(dlAllFund())

code_list = getAllCode()
for code in code_list:
	url = 'http://fund.eastmoney.com/pingzhongdata/'+code+'.js'
	res = requests.get(url)
	print(type(res))


# class backTest():

# 初始化参数
def initialize():
	global balance,oneHand,oneInterval,buyDate,dateIndex,investAmount,myShares,balanceChange,buyInterval,sellThreshold
	balance = 5000
	oneHand = 100
	oneInterval = 500
	buyDate = '1970-1-1'
	dateIndex = -10
	investAmount = 0
	myShares = 0
	balanceChange = []
	# 测试得到的阈值：连续上涨买入间隔时间、止盈收益率
	buyInterval = 4
	sellThreshold = 0.15


# 买入策略：本金不足时放慢买入速度
def checkBuy(index, row):
	global balance, oneHand, dateIndex, buyInterval, returnRate, investAmount, myShares
	if balance < 0:
		# print('Error occurred! Balance is less than 0!')
		return
	elif balance == 0:
		return
	elif index-dateIndex > buyInterval:
		buyAmount = min(oneInterval, balance)
		balance -= buyAmount
		myShares += buyAmount/row['netWorth']
		investAmount += buyAmount
		# print('Buy '+str(int(buyAmount))+' on '+row['Date']+'. Balance:'+str(int(balance))+'. Total investment: '+str(int(investAmount)))
		dateIndex = index
		return
	elif balance < 1000:
		if (index-dateIndex > 3) & (row['Change'] <= -1):
			buyAmount = min(int(np.abs(np.ceil(row['Change']))*oneHand), balance)
			balance -= buyAmount
			myShares += buyAmount/row['netWorth']
			investAmount += buyAmount
			# rint('Buy '+str(int(buyAmount))+' on '+row['Date']+'. Balance: '+str(int(balance))+'. Total investment: '+str(int(investAmount)))
			dateIndex = index
			return
		else:
			return
	elif balance < 2000:
		if (index-dateIndex > 2) & (row['Change'] <= -1):
			buyAmount = min(int(np.abs(np.ceil(row['Change']))*oneHand), balance)
			balance -= buyAmount
			myShares += buyAmount/row['netWorth']
			investAmount += buyAmount
			# print('Buy '+str(int(buyAmount))+' on '+row['Date']+'. Balance: '+str(int(balance))+'. Total investment: '+str(int(investAmount)))
			dateIndex = index
			return
		else:
			return
	else:
		buyAmount = min(int(np.abs(np.ceil(row['Change']))*oneHand), balance)
		balance -= buyAmount
		myShares += buyAmount/row['netWorth']
		investAmount += buyAmount
		# print('Buy '+str(int(buyAmount))+' on '+row['Date']+'. Balance: '+str(int(balance))+'. Total investment: '+str(int(investAmount)))
		dateIndex = index
		return


# 卖出策略：达到止盈收益率后卖出一半
def checkSell(row):
	global balance, investAmount, myShares, balanceChange, sellThreshold
	myCost = investAmount/myShares if myShares != 0 else 0
	returnRate = (row['netWorth']-myCost)/myCost
	# print(returnRate*100)
	if (returnRate >= sellThreshold) & (myShares > 0):
		shares2Sell = myShares/2
		myShares -= shares2Sell
		sellAmount = shares2Sell*row['netWorth']
		balance += sellAmount
		investAmount = myShares*row['netWorth']
		# print('Sell '+str(int(sellAmount))+' on '+row['Date'])
	totalAssest = balance+myShares*row['netWorth']
	balanceChange.append(totalAssest)
	# print(totalAssest)

# 单个基金回测函数
def backTest(code):
	global buyInterval, sellThreshold, balanceChange
	data = pd.read_csv('./fundData/'+code+'.csv')
	if len(data) < 500:
		# print('Ignored newly established fund: '+code)
		return 5000
	else:
		lastYear = data.iloc[-500:]
	for index,row in lastYear.iterrows():
		checkBuy(index, row)
		checkSell(row)
	return balanceChange[-1]



# 测试寻找合适的参数：“连续上涨买入间隔天数”和“止盈收益率”
# def backTest(code, buyInt, sellTh):
# 	global buyInterval, sellThreshold, balanceChange
# 	buyInterval = buyInt
# 	sellThreshold = sellTh
# 	# print('Interval: '+str(buyInterval)+'   Threshold: '+str(sellThreshold))
# 	data = pd.read_csv('./fundData/'+code+'.csv')
# 	last100days = data.iloc[-250:]
# 	for index,row in last100days.iterrows():
# 		checkBuy(index, row)
# 		checkSell(row)
# 	return balanceChange[-1]

# finalRes = 0
# finalResList = []
# my_list = ['162605','020005','000529','005267','001217','006253','161818','005969','005534','007043','002846','005236','000263','004868','570008','005669','001385','001382','001832','006616']
# for buyInt in [4,5,6,7,8,9,10]:
# 	for sellTh in [0.05,0.1,0.15,0.2,0.25,0.3]:
# 		for code in my_list:
# 			initialize()
# 			oneRes = backTest(code, buyInt, sellTh)
# 			finalRes += oneRes
# 		finalRate = (finalRes - 20*5000)/(20*5000)
# 		finalResList.append(finalRes)
# 		print('Interval: '+str(buyInt)+'   Threshold: '+str(sellTh)+'    Return rate: '+str(finalRate))
# 		finalRes = 0

# xx,yy = np.meshgrid([4,5,6,7,8,9,10],[0.05,0.1,0.15,0.2,0.25,0.3])
# zz = np.array(finalResList)
# zz.shape = (7,6)
# zz = np.transpose(zz)
# ax1 = plt.axes(projection='3d')
# ax1.plot_surface(xx,yy,zz,cmap='rainbow')
# plt.show()




# fundFileList = os.listdir('./fundData')
# fundCodeList = []
# for file in fundFileList:
# 	code = file[:-4]
# 	fundCodeList.append(code)
# for code in fundCodeList:
# 	initialize()
# 	result = backTest(code)
# 	if result > 12500:
# 		print('code: '+code+'   amount: '+str(result))

# initialize()
# backTest('006679')
# plt.plot(balanceChange)
# plt.show()
