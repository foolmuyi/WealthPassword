# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import requests
import json
import time
import random
import datetime as dt
import math
import akshare as ak
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing


def get_data(code, start_date, end_date):
    hist_data = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date, adjust='hfq')
    df = hist_data.iloc[:, 0:6]
    df.columns = ['datetime', 'open', 'close', 'high', 'low', 'volume']
    df.index = pd.to_datetime(df.datetime)
    return df


class SimpleStrategy(bt.Strategy):

    params = (
        ('fast_param', 10),
        ('month_param', 20),
        ('quarter_param', 60),
        ('year_param', 250),
        ('days_to_cross', 10),
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.ma_fast = bt.ind.SMA(period = self.params.fast_param)
        self.ma_month = bt.ind.SMA(period = self.params.month_param)
        self.ma_quarter = bt.ind.SMA(period = self.params.quarter_param)
        self.ma_year = bt.ind.SMA(period = self.params.year_param)
        self.stopprice = 0    # modified
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                # self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % (order.executed.price, order.executed.value, order.executed.comm))

                self.buyprice = order.executed.price
                self.stopprice = 0.9*self.buyprice    # modified
                self.buycomm = order.executed.comm
            else:  # Sell
                pass
                # self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % (order.executed.price, order.executed.value, order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        # self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    # 检查均线发散条件
    def checkDiv(self, ago=0, size=5):
        fast_minus_month = pd.Series(self.ma_fast.get(ago=ago, size=size)) - pd.Series(self.ma_month.get(ago=ago, size=size))
        cond_1 = fast_minus_month.equals(fast_minus_month.sort_values())
        month_minus_quarter = pd.Series(self.ma_month.get(ago=ago, size=size)) - pd.Series(self.ma_quarter.get(ago=ago, size=size))
        cond_2 = month_minus_quarter.equals(month_minus_quarter.sort_values())
        quarter_minus_year = pd.Series(self.ma_quarter.get(ago=ago, size=size)) - pd.Series(self.ma_year.get(ago=ago, size=size))
        cond_3 = quarter_minus_year.equals(quarter_minus_year.sort_values())
        if (cond_1 and cond_2 and cond_3):
            return True
        else:
            return False

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if not self.position:
            cond_1_1 = min(pd.Series(self.ma_fast.get(size=10)) - pd.Series(self.ma_month.get(size=10))) > 0    # fast线连续15日高于月线
            cond_1_2 = min(pd.Series(self.ma_month.get(size=5)) - pd.Series(self.ma_quarter.get(size=5))) > 0    # 月线连续10日高于季度线
            cond_1_3 = min(pd.Series(self.ma_quarter.get(size=3)) - pd.Series(self.ma_year.get(size=3))) > 0    # 月线连续10日高于季度线
            cond_1 = cond_1_1 and cond_1_2 and cond_1_3
            cond_2 = (self.data.close[0] > self.ma_fast[0]) and (self.ma_fast[-1] > self.data.close[-1] > self.ma_quarter[-1])    # 收盘价突破fast线
            cond_3 = self.data.close[0] > self.data.open[0]    # 当日收红
            if (cond_1 and cond_2 and cond_3):
                self.order = self.buy()
            else:
                pass
        else:
            self.stopprice = max(0.9*self.data.high[0], self.stopprice)
            # cond_1_1 = (self.data.high[0] > 1.1*self.buyprice and self.data.close[0] < self.ma_quarter[0])    # 止盈
            # cond_1_2 = (self.data.close[-1] > 1.1*self.buyprice and self.data.close[0] < 1.1*self.buyprice)
            # cond_1 = cond_1_1 or cond_1_2
            # cond_1 = self.data.close[0] < self.stopprice
            cond_1 = self.checkDiv(ago=-1, size=5) and not self.checkDiv(ago=0, size=5)    # 若近五日发散趋势结束，止盈
            cond_2 = self.data.close[0] < self.ma_month[0]    # 止损
            if (cond_1 or cond_2):
                self.close()


if __name__ == '__main__':
    code_list = ['002642', '603019', '000617', '000802', '002563', '002076', '603111', '002245', '600562', '002070',
                 '002426', '600628', '603977', '603888', '600385', '000026', '603499', '000603', '600298', '600117',
                 '002674', '603912', '002222', '000692', '002728', '600701', '002919', '603199', '600513', '600543',
                 '603589', '002952', '603558', '000561', '000811', '000933', '603318', '000962', '603920', '600268',
                 '600857', '600352', '600594', '601877', '002196', '002675', '002552', '603385', '002272', '603833',
                 '002641', '002597', '600330', '600843', '000711', '601633', '002850', '000828', '600909', '002052',
                 '600869', '603617', '000709', '600830', '600826', '002568', '601599', '603639', '002292', '603113',
                 '600188', '600695', '002400', '002499', '600210', '002275', '600269', '601609', '002334', '000868',
                 '002553', '002475', '002305', '600828', '603722', '601015', '002909', '002100', '600510', '002101',
                 '000712', '603918', '002905', '600487', '603688', '600415', '000333', '603081', '002261', '600232']
    total_profit = 0
    total_loss = 0
    win_num = 0
    loss_num = 0
    # code_list = ['000692']
    for code in code_list:
        stock_data = get_data(code, '20120610', '20220610')
        # print(stock_data.head(600).to_string())
        data = bt.feeds.PandasData(dataname=stock_data)
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(SimpleStrategy)
        # # cerebro.optstrategy(SingleEMAStrategy,trend_param=range(600,700,10))
        cerebro.broker.setcash(10000)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addsizer(bt.sizers.PercentSizer,percents=90)

        cerebro.run()
        print(code + '  Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
        if cerebro.broker.getvalue() > 10000:
            total_profit += (cerebro.broker.getvalue() - 10000)
            win_num += 1
        elif cerebro.broker.getvalue() < 10000:
            total_loss += (cerebro.broker.getvalue() - 10000)
            loss_num += 1
        else:
            pass

        # cerebro.plot(style='candle')

    average_profit = total_profit/win_num
    average_loss = total_loss/loss_num
    overall_average_profit = (total_profit + total_loss)/(win_num + loss_num)
    win_rate = win_num/(win_num + loss_num)
    print('Average profit: %.2f' % (average_profit))
    print('Average loss: %.2f' % (average_loss))
    print('Overall average loss: %.2f' % (overall_average_profit))
    print('Win rate: %.2f' % (win_rate))
    print('Decision value: %.2f' % (-average_profit/average_loss*win_rate))







# 寻找最佳参数组合
# pool = multiprocessing.Pool(6)
# manager = multiprocessing.Manager()
# param_comb = manager.dict()
# for trend_param in range(10,200,5):
#   pool.apply_async(Backtester(3,6).test,(trend_param,))

# pool.close()
# pool.join()

# result = dict(sorted(param_comb.items(), key=lambda x: x[0]))
# x_keys = []
# y_values = []
# for each in result.items():
#   x_keys.append(str(each[0]))
#   y_values.append(each[1])
# plt.plot(x_keys,y_values)
# ax = plt.axes()
# ax.xaxis.set_major_locator(plt.MultipleLocator(10))
# plt.show()