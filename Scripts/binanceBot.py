# -*- coding:utf-8 -*-

import json,time
import requests
import hmac,hashlib
import numpy as np
import smtplib
from email.mime.text import MIMEText


# This script runs every 15 minutes


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

# acquire marker price
def getMakerPrice(API_key,API_secret):
	info_url = 'https://fapi.binance.com//fapi/v1/ticker/bookTicker'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD'}
	res = requests.get(url=info_url,params=query_string)
	return res

# order at market price (stop loss mainly)
def order(API_key,API_secret,side,quantity):
	order_url = 'https://fapi.binance.com/fapi/v1/order'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','side':side,'type':'MARKET','quantity':quantity,'timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.post(url=order_url,headers={'X-MBX-APIKEY':API_key},data=query_string)
	return res

# order as marker (open positions)
def order_maker(API_key,API_secret,side,quantity):
	order_url = 'https://fapi.binance.com/fapi/v1/order'
	timestamp = int(time.time()*1000)
	maker_price_raw = getMakerPrice(API_key,API_secret)
	maker_price_info = json.loads(maker_price_raw.text)
	if side == 'BUY':
		maker_price = float(maker_price_info['bidPrice'])
	elif side == 'SELL':
		maker_price = float(maker_price_info['askPrice'])
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
	return res

# close current open order
def closeOpenOrders(API_key,API_secret):
	info_url = 'https://fapi.binance.com//fapi/v1/allOpenOrders'
	timestamp = int(time.time()*1000)
	query_string = {'symbol':'ETHBUSD','timestamp':timestamp}
	query_string['signature'] = getSig(API_secret,param2string(query_string))
	res = requests.delete(url=info_url,headers={'X-MBX-APIKEY':API_key},params=query_string)
	return res

def getPositionAndPrice(API_key,API_secret):
	account_info_res = getAccountInfo(API_key,API_secret)
	account_info = json.loads(account_info_res.text)
	ETHBUSD_info = [each for each in account_info['positions'] if each['symbol'] == 'ETHBUSD'][-1]
	positionAmt = float(ETHBUSD_info['positionAmt'])    # current position
	entry_price = float(ETHBUSD_info['entryPrice'])
	return positionAmt,entry_price

# send email to me when error occures
def sendMail(mail_content,subject='Error Occurred!'):
	mail_host = 'smtp.163.com'
	mail_username = 'example@163.com'
	mail_pw = 'passwordexample'
	mail_recv = ['example@xxx.com']
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
	quantity = 0.04
	# setLeverage(API_key,API_secret)    # for test
	positionAmt, entry_price = getPositionAndPrice(API_key,API_secret)
	close_price = getData()[:-1]    # delete the last price because the last one is current price
	ema_fast = ema(close_price,fast_factor)
	ema_slow = ema(close_price,slow_factor)

	# close open orders
	open_orders = json.loads(getOpenOrders(API_key,API_secret).text)
	if open_orders != []:
		closeOpenOrders(API_key,API_secret)
	else:
		pass

	# # 平仓
	if positionAmt > 0:
		if ema_fast[-1] < ema_slow[-1]:    # 趋势反转，平多
			order(API_key,API_secret,'SELL',positionAmt)
		elif (close_price[-1]-entry_price)/entry_price < -0.008:    # 止损
			order(API_key,API_secret,'SELL',positionAmt)
		elif (close_price[-1]-entry_price)/entry_price > 0.008:    # 止盈
			order_maker(API_key,API_secret,'SELL',positionAmt)
	elif positionAmt < 0:
		if ema_fast[-1] > ema_slow[-1]:    # 趋势反转，平空
			order(API_key,API_secret,'BUY',-positionAmt)
		elif (close_price[-1]-entry_price)/entry_price < -0.008:    # 止盈
			order_maker(API_key,API_secret,'BUY',-positionAmt)
		elif (close_price[-1]-entry_price)/entry_price > 0.008:    # 止损
			order(API_key,API_secret,'BUY',-positionAmt)
	else:
		pass

	# wait maker order to complete
	time.sleep(5)
	
	# check current position again before open position
	positionAmt, _ = getPositionAndPrice(API_key,API_secret)

	# 建仓
	if (ema_fast[-2] < ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1]) and (positionAmt == 0):
		order(API_key,API_secret,'BUY',quantity)
	elif (ema_fast[-2] > ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1]) and (positionAmt == 0):
		order(API_key,API_secret,'SELL',quantity)
	else:
		pass


if __name__ == "__main__":
	try:
		run()
	except Exception as e:
		sendMail(str(e))