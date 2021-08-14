# -*- coding:utf-8 -*-

import json,time
import requests
import hmac,hashlib
import numpy as np
import traceback
import smtplib
from email.mime.text import MIMEText


# calcute ema
def ema(data,period):
	if period <= 0:
		raise IndexError('Period is '+str(period)+', which is less than 1')
	elif len(data) < period:
		raise IndexError('Cannot obtain EMA because the length of the data list is '+str(len(data))+' while the period is '+str(period))
	else:
		ema_list = []
		for i in range(len(data)):
			if i == 0:
				ema_list.append(round(data[0],2))
			else:
				ema_today = (2*data[i]+(period-1)*ema_list[i-1])/(period+1)
				ema_list.append(round(ema_today,2))
	return ema_list

# acquire k line data
def getData():
	kline_url = 'https://fapi.binance.com/fapi/v1/klines?symbol=ETHBUSD&interval=15m&limit=1500'
	res = requests.get(kline_url)
	raw_data = json.loads(res.text)
	# open_price = [each[1] for each in raw_data]
	close_price = [float(each[4]) for each in raw_data]
	return close_price

# tool function
def param2string(param):
    s=''
    for k in param.keys():
        s+=k
        s+='='
        s+=str(param[k])
        s+='&'
    return s[:-1]

# hash signature
def getSig(API_secret,query_string):
	return hmac.new(API_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

# set leverage (for test)
def setLeverage(API_key,API_secret):
	leverage_url = 'https://fapi.binance.com/fapi/v1/leverage'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','leverage':5,'timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.post(url=leverage_url,headers={'X-MBX-APIKEY':API_key},data=query_string)
	return res

# acquire account info (position amount mainly)
def getAccountInfo(API_key,API_secret):
	info_url = 'https://fapi.binance.com/fapi/v2/account'
	timestamp = int(time.time()*1000)
	query_string = {'timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.get(url=info_url,headers={'X-MBX-APIKEY':API_key},params=query_string)
	return res

# acquire account balance
def getBalance(API_key,API_secret,asset):
	info_url = 'https://fapi.binance.com/fapi/v2/balance'
	timestamp = int(time.time()*1000)
	query_string = {'timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.get(url=info_url,headers={'X-MBX-APIKEY':API_key},params=query_string)
	balance_raw = json.loads(res.text)
	asset_balance_info = [each for each in balance_raw if each['asset'] == asset][0]
	asset_balance = float(asset_balance_info['availableBalance'])
	return asset_balance

# acquire mark price
def getMarkPrice(API_key,API_secret,symbol):
	info_url = 'https://fapi.binance.com/fapi/v1/premiumIndex'
	query_string = {'symbol':symbol}
	res = requests.get(url=info_url,params=query_string)
	mark_price_raw = json.loads(res.text)
	mark_price = float(mark_price_raw['markPrice'])
	return mark_price

# acquire maker price
def getMakerPrice(API_key,API_secret,side):
	info_url = 'https://fapi.binance.com//fapi/v1/ticker/bookTicker'
	query_string = {'symbol':'ETHBUSD'}
	res = requests.get(url=info_url,params=query_string)
	maker_price_info = json.loads(res.text)
	if side == 'BUY':
		maker_price = float(maker_price_info['bidPrice'])
	elif side == 'SELL':
		maker_price = float(maker_price_info['askPrice'])
	return maker_price

# order at market price (stop loss mainly)
def order(API_key,API_secret,side,quantity):
	order_url = 'https://fapi.binance.com/fapi/v1/order'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','side':side,'type':'MARKET','quantity':quantity,'timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.post(url=order_url,headers={'X-MBX-APIKEY':API_key},data=query_string)
	return res

# order as maker (open positions)
def order_maker(API_key,API_secret,side,quantity):
	order_url = 'https://fapi.binance.com/fapi/v1/order'
	timestamp = int(time.time()*1000)
	maker_price = getMakerPrice(API_key,API_secret,side)
	query_string = {'symbol':'ETHBUSD','side':side,'type':'LIMIT','quantity':quantity,'price':maker_price,'timeInForce':'GTX','timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.post(url=order_url,headers={'X-MBX-APIKEY':API_key},data=query_string)
	return res

# acquire current open order
def getOpenOrders(API_key,API_secret):
	info_url = 'https://fapi.binance.com/fapi/v1/openOrders'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.get(url=info_url,headers={'X-MBX-APIKEY':API_key},params=query_string)
	open_orders = json.loads(res.text)
	return open_orders

# close current open order
def closeOpenOrders(API_key,API_secret):
	info_url = 'https://fapi.binance.com//fapi/v1/allOpenOrders'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.delete(url=info_url,headers={'X-MBX-APIKEY':API_key},params=query_string)
	return res

# get position and entry price
def getPositionAndPrice(API_key,API_secret):
	account_info_res = getAccountInfo(API_key,API_secret)
	account_info = json.loads(account_info_res.text)
	ETHBUSD_info = [each for each in account_info['positions'] if each['symbol'] == 'ETHBUSD'][-1]
	positionAmt = float(ETHBUSD_info['positionAmt'])    # current position
	entry_price = float(ETHBUSD_info['entryPrice'])
	return positionAmt,entry_price

# calculate order quantity
def getMyQuantity(API_key,API_secret,leverage):
	balance = getBalance(API_key,API_secret,'BUSD')
	mark_price = getMarkPrice(API_key,API_secret,'ETHBUSD')
	quantity = round(balance*leverage/3/mark_price,3)
	return quantity

# try to order as maker for 10 times
def orderMaker10Times(API_key,API_secret,side,quantity):
	closeOpenOrders(API_key,API_secret)
	# initial position amount. 0 when open new position, real position when take profit
	initPositionAmt, _ = getPositionAndPrice(API_key,API_secret)
	positionAmt, _ = getPositionAndPrice(API_key,API_secret)
	count = 1
	while (positionAmt == initPositionAmt) and (count <= 10):
		order_maker(API_key,API_secret,side,quantity)
		time.sleep(3)
		closeOpenOrders(API_key,API_secret)
		positionAmt, _ = getPositionAndPrice(API_key,API_secret)
		count += 1

# calculate current ROE
def calcROE(API_key,API_secret,symbol='ETHBUSD'):
	positionAmt, entry_price = getPositionAndPrice(API_key,API_secret)
	mark_price = getMarkPrice(API_key,API_secret,symbol)
	if positionAmt > 0:
		ROE = round((mark_price-entry_price)/entry_price*100,2)
	elif positionAmt < 0:
		ROE = round((entry_price-mark_price)/entry_price*100,2)
	else:
		ROE = 0
	return ROE

# write stopROE value to file
def writeStopROE(stopROE,path='/home/username/BinanceBot/stopROE.json'):
	with open(path,'w') as f:
		f.write(str(stopROE))

# read stopROE value from file
def getStopROE(path='/home/username/BinanceBot/stopROE.json'):
	with open(path,'r') as f:
		stopROE = json.load(f)
	return stopROE


# send email to me when error occures
def sendMail(mail_content,subject='Error Occurred!'):
	mail_host = 'smtp.163.com'
	mail_username = 'example@163.com'
	mail_pw = 'EMAILPASSWORD'
	mail_recv = ['example@example.com']
	message = MIMEText(mail_content,'plain','utf-8')
	message['Subject'] = subject
	message['From'] = 'example@163.com'
	message['To'] = mail_recv[0]
	smtpObj = smtplib.SMTP_SSL(mail_host,465)
	smtpObj.login(mail_username,mail_pw)
	smtpObj.sendmail(mail_username,mail_recv[0],message.as_string())
	smtpObj.quit()


# main function
def run():
	API_key = 'APIKEYEXAMPLE'
	API_secret = 'APISECRETEXAMPLE'
	fast_factor = 3
	slow_factor = 6
	leverage = 10
	# setLeverage(API_key,API_secret)    # for test
	positionAmt, entry_price = getPositionAndPrice(API_key,API_secret)
	close_price = getData()[:-1]    # remove the last data point because it is current price
	ema_fast = ema(close_price,fast_factor)
	ema_slow = ema(close_price,slow_factor)

	# close open orders
	closeOpenOrders(API_key,API_secret)

	# close position to stop loss (trend reverse situation)
	if (positionAmt > 0) and (ema_fast[-1] < ema_slow[-1]):    # trend reversed, close long position
		order(API_key,API_secret,'SELL',positionAmt)    # close position
		stopROE = -0.8    # reset stopROE after close position
		time.sleep(1)    # wait close position order to complete
	elif (positionAmt < 0) and (ema_fast[-1] > ema_slow[-1]):    # trend reversed, close short position
		order(API_key,API_secret,'BUY',-positionAmt)    # close position
		stopROE = -0.8    # reset stopROE after close position
		time.sleep(1)    # wait close position order to complete
	else:
		pass

	# trailing stop
	positionAmt, entry_price = getPositionAndPrice(API_key,API_secret)
	stopROE = getStopROE()
	if positionAmt != 0:
		ROE = calcROE(API_key,API_secret)
		if ROE < stopROE:    # close position
			if positionAmt > 0:
				orderMaker10Times(API_key,API_secret,'SELL',positionAmt)
				stopROE = -0.8    # reset stopROE after close position
			elif positionAmt < 0:
				orderMaker10Times(API_key,API_secret,'BUY',-positionAmt)
				stopROE = -0.8    # reset stopROE after close position
			else:
				pass
		elif ROE > 11.5:
			stopROE = max(10.3,stopROE)
		elif ROE > 10.3:
			stopROE = max(9.2,stopROE)
		elif ROE > 9.2:
			stopROE = max(8.1,stopROE)
		elif ROE > 8.1:
			stopROE = max(7.1,stopROE)
		elif ROE > 7.1:
			stopROE = max(6.1,stopROE)
		elif ROE > 6.1:
			stopROE = max(5.2,stopROE)
		elif ROE > 5.2:
			stopROE = max(4.3,stopROE)
		elif ROE > 4.3:
			stopROE = max(3.5,stopROE)
		elif ROE > 3.5:
			stopROE = max(2.7,stopROE)
		elif ROE > 2.7:
			stopROE = max(2,stopROE)
		elif ROE > 2:
			stopROE = max(1.3,stopROE)
		elif ROE > 1.3:
			stopROE = max(0.7,stopROE)
		elif ROE > 0.7:
			stopROE = max(0.1,stopROE)
	
	# check current position again before open position
	positionAmt, _ = getPositionAndPrice(API_key,API_secret)

	# get quantity to open new order
	quantity = getMyQuantity(API_key,API_secret,leverage)

	# open position
	if (ema_fast[-2] < ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1]) and (positionAmt == 0):
		orderMaker10Times(API_key,API_secret,'BUY',quantity)
		stopROE = -0.8
	elif (ema_fast[-2] > ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1]) and (positionAmt == 0):
		orderMaker10Times(API_key,API_secret,'SELL',quantity)
		stopROE = -0.8
	else:
		pass

	# save stopROE value to file
	writeStopROE(stopROE)


if __name__ == "__main__":
	try:
		run()
	except Exception as e:
		sendMail(traceback.format_exc())