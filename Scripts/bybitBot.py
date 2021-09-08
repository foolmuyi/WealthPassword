# -*- coding:utf-8 -*-

'''
    A trading bot for Bybit USDT Perpetual
'''

import os
import json
import time
import requests
import hmac
import hashlib
import numpy as np
import smtplib
import traceback
from email.mime.text import MIMEText
from tenacity import *

# proxies = {
#     'http': 'http://127.0.0.1:8888',
#     'https': 'https://127.0.0.1:8888' 
#   }

proxies = None


# send email to me when error occures
def sendMail(mail_content,subject='Bybit Error Occurred!'):
    mail_host = 'smtp.163.com'
    mail_username = ''
    mail_pw = ''
    mail_recv = ['']
    message = MIMEText(mail_content,'plain','utf-8')
    message['Subject'] = subject
    message['From'] = ''
    message['To'] = mail_recv[0]
    smtpObj = smtplib.SMTP_SSL(mail_host,465)
    smtpObj.login(mail_username,mail_pw)
    smtpObj.sendmail(mail_username,mail_recv[0],message.as_string())
    smtpObj.quit()


class TradeBot(object):

    # parameters initialization
    def __init__(self,symbol):
        self.base_url = 'https://api.bybit.com'
        self.API_key = ''
        self.API_secret = ''
        self.symbol = symbol
        self.coin = 'USDT'
        self.trend_param = 400
        self.leverage = 10
        self.ROE_file = '/home/ubuntu/BybitBot/USDT/stopROE_'+self.symbol+'.json'

    # calcute ema
    def ema(self,data,period):
        if period <= 0:
            raise IndexError('Period is '+str(period)+', which is less than 1')
        elif len(data) < period:
            raise IndexError('Cannot obtain EMA because the length of the data list is '+str(len(data))+' while the period is '+str(period))
        else:
            ema_list = []
            for i in range(len(data)):
                if i == 0:
                    ema_list.append(round(data[0],5))
                else:
                    ema_today = (2*data[i]+(period-1)*ema_list[i-1])/(period+1)
                    ema_list.append(round(ema_today,5))
        return ema_list

    # acquire k line data
    def getData(self):
        interval = 5    # 5 minutes
        limit = 200    # bybit limits max to 200 per page
        page = 1    # 200 per page
        page_limit = 5    # get data from page 1 to 5
        open_price = []
        close_price = []
        try_times = 0    # try x time if failed to get data
        while (page < page_limit) and (try_times < 5):
            ts = str(int(time.time())-page*limit*interval*60)
            try:
                kline_url = self.base_url+'/public/linear/kline?'+'symbol='+self.symbol+'&interval='+str(interval)+'&from='+ts+'&limit=200'
                res = requests.get(kline_url,proxies=proxies)
                raw_data = json.loads(res.text)['result']
                open_price_one_page = [float(each['open']) for each in raw_data]
                close_price_one_page = [float(each['close']) for each in raw_data]
            except Exception as e:
                try_times += 1
                continue
            close_price = close_price_one_page + close_price
            open_price = open_price_one_page + open_price
            page += 1
        price_data = {'open_price':open_price,'close_price':close_price}
        # check if the data if broken
        if (len(price_data['open_price']) == (page_limit-1)*limit) and (len(price_data['close_price']) == (page_limit-1)*limit):
            pass
        else:
            price_data = None    # data broken. set price_data to None to trigger error and prevent trading
        return price_data

    # tool function
    def param2string(self,params):
        sign = ''
        for key in sorted(params.keys()):
            v = params[key]
            if isinstance(params[key], bool):
                if params[key]:
                    v = 'true'
                else :
                    v = 'false'
            sign += key + '=' + v + '&'
        return sign[:-1]

    # hash signature
    def getSig(self,query_string):
        return hmac.new(self.API_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    # get position and entry price
    @retry(stop=stop_after_attempt(5),wait=wait_fixed(1),retry=retry_if_result(lambda x: x is None))
    def getPositionInfo(self):
        position_url = self.base_url+'/private/linear/position/list'
        ts = str(int(time.time()*1000))
        query_string = {'api_key':self.API_key,'symbol':self.symbol,'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.get(url = position_url,params=query_string,proxies=proxies)
        pos_info = json.loads(res.text)['result']
        return pos_info

    # acquire account balance
    def getBalance(self):
        balance_url = self.base_url+'/v2/private/wallet/balance'
        ts = str(int(time.time()*1000))
        query_string = {'api_key':self.API_key,'coin':self.coin,'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.get(url=balance_url,params=query_string,proxies=proxies)
        raw_data = json.loads(res.text)['result'][self.coin]
        balance = raw_data['available_balance']
        return balance

    # acquire lastest information for specific symbol
    def getFuturesInfo(self):
        info_url = self.base_url+'/v2/public/tickers?'+'symbol='+self.symbol
        res = requests.get(info_url,proxies=proxies)
        info_data = json.loads(res.text)['result'][0]
        return info_data

    # acquire maker price
    def getMakerPrice(self,side):
        info_data = self.getFuturesInfo()
        if side == 'Buy':
            maker_price = float(info_data['bid_price'])
        elif side == 'Sell':
            maker_price = float(info_data['ask_price'])
        return maker_price

    # order at market price (stop loss)
    def order(self,side,quantity,reduce_only='False'):
        order_url = self.base_url+'/private/linear/order/create'
        ts = str(int(time.time()*1000))
        maker_price = self.getMakerPrice(side)
        if side == 'Buy':
            stop_loss_price = maker_price*(1-0.01)    # set a auto stop loss price in case the cloud server crashes
        elif side == 'Sell':
            stop_loss_price = maker_price*(1+0.01)
        else:
            pass
        query_string = {'api_key':self.API_key,'side':side,'symbol':self.symbol,'order_type':'Market','qty':str(quantity),'time_in_force':'GoodTillCancel',
        'close_on_trigger':'False','stop_loss':str(stop_loss_price),'reduce_only':str(reduce_only),'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.post(url=order_url,data=query_string,proxies=proxies)
        return res

    # order as maker (open positions)
    def order_maker(self,side,quantity):
        order_url = self.base_url+'/private/linear/order/create'
        ts = str(int(time.time()*1000))
        maker_price = self.getMakerPrice(side)
        if side == 'Buy':
            stop_loss_price = maker_price*(1-0.01)    # set a auto stop loss price in case the cloud server crashes
        elif side == 'Sell':
            stop_loss_price = maker_price*(1+0.01)
        else:
            pass
        query_string = {'api_key':self.API_key,'side':side,'symbol':self.symbol,'order_type':'Limit','qty':str(quantity),'price':str(maker_price),
        'time_in_force':'PostOnly','close_on_trigger':'False','stop_loss':str(stop_loss_price),'reduce_only':'False','timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.post(url=order_url,data=query_string,proxies=proxies)
        res_data = json.loads(res.text)['result']
        return res_data

    # # acquire current open order
    # def getOpenOrders(self):
    #   order_list_url = self.base_url+'/private/linear/order/list'
    #   ts = str(int(time.time()*1000))
    #   query_string = {'api_key':self.API_key,'symbol':self.symbol,'order_status':'New','timestamp':ts}
    #   query_string['sign'] = self.getSig(self.param2string(query_string))
    #   res = requests.get(url=order_list_url,params=query_string,proxies=proxies)
    #   raw_data = json.loads(res.text)

    # cancel open orders by order_id
    def cancelOpenOrders(self,order_id):
        cancel_url = self.base_url+'/private/linear/order/cancel'
        ts = str(int(time.time()*1000))
        query_string = {'api_key':self.API_key,'symbol':self.symbol,'order_id':order_id,'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.post(url=cancel_url,data=query_string,proxies=proxies)
        return res

    # cancel current open order
    def cancelAllOpenOrders(self):
        cancel_url = self.base_url+'/private/linear/order/cancel-all'
        ts = str(int(time.time()*1000))
        query_string = {'api_key':self.API_key,'symbol':self.symbol,'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.post(url=cancel_url,data=query_string,proxies=proxies)
        return res

    # calculate order quantity
    def getMyQuantity(self):
        balance = self.getBalance()
        last_price = float(self.getFuturesInfo()['last_price'])
        quantity = round(balance*self.leverage/3/last_price,3)    # 3 means using 1/3 of balance to open position everytime
        return quantity

    # acuqire position amount
    def getPosAmt(self):
        pos_info = self.getPositionInfo()
        buy_pos_amt = [each['size'] for each in pos_info if each['side'] == 'Buy'][0]
        sell_pos_amt = [each['size'] for each in pos_info if each['side'] == 'Sell'][0]
        pos_amt = buy_pos_amt-sell_pos_amt
        return pos_amt

    # try to order as maker for multiple times
    def orderMakerMultiTimes(self,side,quantity):
        count = 1
        pos_amt = self.getPosAmt()
        while (pos_amt != quantity) and (count <= 15):
            try:
                order_id = self.order_maker(side,round(quantity-abs(pos_amt),3))['order_id']
            except:
                count += 1
                continue
            time.sleep(2.5)
            self.cancelOpenOrders(order_id)
            pos_amt = self.getPosAmt()
            count += 1

    # calculate current ROE
    def calcROE(self):
        pos_amt = self.getPosAmt()
        pos_info = self.getPositionInfo()
        last_price = float(self.getFuturesInfo()['last_price'])
        if pos_amt > 0:
            entry_price = [each['entry_price'] for each in pos_info if each['side'] == 'Buy'][0]
            ROE = round((last_price-entry_price)/entry_price*100,2)
        elif pos_amt < 0:
            entry_price = [each['entry_price'] for each in pos_info if each['side'] == 'Sell'][0]
            ROE = round((entry_price-last_price)/entry_price*100,2)
        else:
            ROE = 0
        return ROE

    # set stop_ROE value to stop_loss
    def setStopLoss(self,side,stop_price):
        set_url = self.base_url+'/private/linear/position/trading-stop'
        ts = str(int(time.time()*1000))
        query_string = {'api_key':self.API_key,'symbol':self.symbol,'side':side,'stop_loss':str(stop_price),'timestamp':ts}
        query_string['sign'] = self.getSig(self.param2string(query_string))
        res = requests.post(url=set_url,data=query_string,proxies=proxies)

    # write stopROE value to file
    def writeStopROE(self,stop_ROE):
        path=self.ROE_file
        with open(path,'w') as f:
            f.write(str(stop_ROE))

    # read stopROE value from file
    def getStopROE(self):
        path=self.ROE_file
        with open(path,'r') as f:
            stop_ROE = json.load(f)
        return stop_ROE


    # main function
    def run(self):
        price_data = self.getData()
        open_price = price_data['open_price'][:-1]    # remove the data of the current bar
        close_price = price_data['close_price'][:-1]    # remove the data of the current bar
        ema_trend = self.ema(close_price,self.trend_param)

        # cancel all open orders
        self.cancelAllOpenOrders()

        pos_amt = self.getPosAmt()
        # close position to stop loss (trend reverse situation)
        if (pos_amt > 0) and (max(open_price[-1],close_price[-1]) < ema_trend[-1]):    # trend reversed, close long position
            self.order('Sell',abs(pos_amt),reduce_only=True)    # close position
            time.sleep(1)    # wait close position order to complete
            # self.orderMakerMultiTimes('Sell',pos_amt)    # TODO: add reduce_only param to close position
        elif (pos_amt < 0) and (min(open_price[-1],close_price[-1]) > ema_trend[-1]):    # trend reversed, close short position
            self.order('Buy',abs(pos_amt),reduce_only=True)    # close position
            time.sleep(1)    # wait close position order to complete
            # self.orderMakerMultiTimes('Buy',pos_amt)    # TODO: add reduce_only param to close position
        else:
            pass

        # trailing stop
        pos_amt = self.getPosAmt()
        stop_ROE = self.getStopROE()
        # pos_info = self.getPositionInfo()
        # # calc current stop_ROE
        # if pos_amt > 0:
        #     side = 'Buy'
        #     entry_price = [each['entry_price'] for each in pos_info if each['side'] == side][0]
        #     stop_price = [each['stop_loss'] for each in pos_info if each['side'] == side][0]
        #     stop_ROE = round((stop_price-entry_price)/entry_price*100,2)
        # elif pos_amt < 0:
        #     side = 'Sell'
        #     entry_price = [each['entry_price'] for each in pos_info if each['side'] == side][0]
        #     stop_price = [each['stop_loss'] for each in pos_info if each['side'] == side][0]
        #     stop_ROE = round((entry_price-stop_price)/entry_price*100,2)
        # else:
        #     pass
        # calc new stop_ROE
        if pos_amt != 0:
            ROE = self.calcROE()
            if ROE < stop_ROE:    # close position
                if pos_amt > 0:
                    self.order('Sell',abs(pos_amt),reduce_only=True)
                elif pos_amt < 0:
                    self.order('Buy',abs(pos_amt),reduce_only=True)
                else:
                    pass
            else:
                stop_ROE = max(round(0.9*ROE-0.7,1),stop_ROE)
        # # calc and set stop_price
        # if pos_amt > 0:
        #     stop_price = round((1+stop_ROE/100)*entry_price,1)
        #     self.setStopLoss('Buy',stop_price)
        # elif pos_amt < 0:
        #     stop_price = round((1-stop_ROE/100)*entry_price,1)
        #     self.setStopLoss('Sell',stop_price)
        # else:
        #     pass

        # check position amount again before open position
        pos_amt = self.getPosAmt()

        # get quantity to open new order
        qty = self.getMyQuantity()

        # open position
        if (open_price[-2] < ema_trend[-2] < close_price[-2]) and (min(open_price[-1],close_price[-1]) > ema_trend[-1]) and (pos_amt == 0):
            # self.orderMakerMultiTimes('Buy',qty)
            self.order('Buy',qty)
            stop_ROE = -0.7
        elif (open_price[-2] > ema_trend[-2] > close_price[-2]) and (max(open_price[-1],close_price[-1]) < ema_trend[-1]) and (pos_amt == 0):
            # self.orderMakerMultiTimes('Sell',qty)
            self.order('Sell',qty)
            stop_ROE = -0.7
        else:
            pass

        # save stopROE value to file
        self.writeStopROE(stop_ROE)


if __name__ == "__main__":
    try:
        bot1 = TradeBot('ETHUSDT')
        bot1.run()
        bot2 = TradeBot('LTCUSDT')
        bot2.run()
        bot3 = TradeBot('SOLUSDT')
        bot3.run()
    except Exception as e:
        sendMail(traceback.format_exc())