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
    hist_data = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date, adjust='qfq')
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
    def checkDiv(self):
        fast_minus_month = pd.Series(self.ma_fast.get(size=5)) - pd.Series(self.ma_month.get(size=5))
        cond_1 = fast_minus_month.equals(fast_minus_month.sort_values())
        month_minus_quarter = pd.Series(self.ma_month.get(size=5)) - pd.Series(self.ma_quarter.get(size=5))
        cond_2 = month_minus_quarter.equals(month_minus_quarter.sort_values())
        quarter_minus_year = pd.Series(self.ma_quarter.get(size=5)) - pd.Series(self.ma_year.get(size=5))
        cond_3 = quarter_minus_year.equals(quarter_minus_year.sort_values())
        if (cond_1 and cond_2 and cond_3):
            return True
        else:
            return False

    # 检查均线发散趋势是否改变，用于判断顶部
    def checkNotDiv(self):
        fast_minus_month = pd.Series(self.ma_fast.get(size=6)) - pd.Series(self.ma_month.get(size=6))
        cond_1 = not fast_minus_month.equals(fast_minus_month.sort_values())
        month_minus_quarter = pd.Series(self.ma_month.get(size=6)) - pd.Series(self.ma_quarter.get(size=6))
        cond_2 = not month_minus_quarter.equals(month_minus_quarter.sort_values())
        quarter_minus_year = pd.Series(self.ma_quarter.get(size=6)) - pd.Series(self.ma_year.get(size=6))
        cond_3 = not quarter_minus_year.equals(quarter_minus_year.sort_values())
        if (cond_1 or cond_2 or cond_3):
            return True
        else:
            return False

    # 从当前点向前寻找趋势首日
    def findDDay(self):
        for i in range(len(self) - self.params.year_param + 1):    # 从第self.params.year_param日开始才有年线
            if (self.ma_fast[-i] > self.ma_month[-i] > self.ma_quarter[-i]):
                continue
            # cond_1 = (self.ma_month[-i] - self.ma_quarter[-i]) > (self.ma_month[-i-1] - self.ma_quarter[-i-1])
            # cond_2 = (self.ma_quarter[-i] - self.ma_year[-i]) > (self.ma_quarter[-i-1] - self.ma_year[-i-1])
            # if (self.ma_month[-i] < self.ma_quarter[-i]):    # 月线上穿季度线，不再向前找
            #     break
            # elif cond_1 and cond_2:
            #     continue
            else:
                break
        return i

    # 计算本次回撤是趋势形成以来的第几次回撤
    def countDrawdowns(self, days):
        drawdowns = 0
        if days <= 5:
            drawdowns = 0
        else:
            for i in range(days-5):
                cond_1 = self.data.close[-i] < self.ma_fast[-i]    # 当日收盘低于fast线
                cond_2 = min(pd.Series(self.data.close.get(ago=-i-1, size=5)) - pd.Series(self.ma_fast.get(ago=-i-1, size=5))) >= 0    # 前5日收盘均高于fast线
                if cond_1 and cond_2:
                    drawdowns += 1
        return drawdowns

    # 计算本次回撤是趋势形成以来的第几次回撤
    def findDrawdownDay(self, days):
        ago_days = 0
        if days <= 5:
            ago_days = 0
        else:
            for i in range(days-5):
                cond_1 = self.data.close[-i] < self.ma_fast[-i]    # 当日收盘低于fast线
                cond_2 = min(pd.Series(self.data.close.get(ago=-i-1, size=5)) - pd.Series(self.ma_fast.get(ago=-i-1, size=5))) >= 0    # 前5日收盘均高于fast线
                if cond_1 and cond_2:
                    ago_days = i+1
                    break
        return ago_days

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
            # cond_1_1 = min(pd.Series(self.ma_fast.get(size=15)) - pd.Series(self.ma_month.get(size=15))) > 0    # fast线连续15日高于月线
            # # cond_1_2 = min(pd.Series(self.ma_month.get(size=10)) - pd.Series(self.ma_quarter.get(size=10))) > 0    # 月线连续10日高于季度线
            # cond_1_2 = ((list(self.ma_quarter.get(size=5))) == sorted(list(self.ma_quarter.get(size=5))))
            # month_minus_quarter = pd.Series(self.ma_month.get(size=10)) - pd.Series(self.ma_quarter.get(size=10))
            # cond_1_3 = month_minus_quarter.equals(month_minus_quarter.sort_values())
            # cond_1_4 = self.ma_quarter[0] > self.ma_year[0]    # 季度线高于年线
            # cond_1 = cond_1_1 and cond_1_2 and cond_1_3 and cond_1_4
            # cond_2 = (self.data.close[0] > self.ma_fast[0]) and (self.ma_fast[-1] > self.data.close[-1] > self.ma_quarter[-1])    # 收盘价突破fast线
            # cond_3 = self.data.close[0] > self.data.open[0]    # 当日收红
            # if (cond_1 and cond_2 and cond_3):
            #     days_count = self.findDDay()
            #     # 自从趋势形成K线始终运行于fast线上方(只做第一次回调)
            #     cond_4 = (self.countDrawdowns(days_count) == 1)
            #     if cond_4:
            #         self.order = self.buy()
            cond_1_1 = min(pd.Series(self.ma_fast.get(size=10)) - pd.Series(self.ma_month.get(size=10))) > 0    # fast线连续10日高于月线
            # cond_1_2 = min(pd.Series(self.ma_month.get(size=5)) - pd.Series(self.ma_quarter.get(size=5))) > 0    # 月线连续5日高于季度线
            trend_days = self.findDDay()
            ago_days = self.findDrawdownDay(trend_days)
            month_minus_quarter = pd.Series(self.ma_month.get(ago=ago_days, size=9)) - pd.Series(self.ma_quarter.get(ago=ago_days, size=9))
            cond_1_2 = month_minus_quarter.equals(month_minus_quarter.sort_values())
            cond_1_3 = min(pd.Series(self.ma_quarter.get(size=3)) - pd.Series(self.ma_year.get(size=3))) > 0    # 季度线连续3日高于年线
            cond_1 = cond_1_1 and cond_1_2 and cond_1_3
            cond_2 = (self.data.close[0] > self.ma_fast[0]) and (self.ma_fast[-1] > self.data.close[-1] > self.ma_quarter[-1])    # 收盘价突破fast线
            cond_3 = self.data.close[0] > self.data.open[0]    # 当日收红
            if (cond_1 and cond_2 and cond_3):
                self.order = self.buy()
                # days_count = self.findDDay()
                # # 自从趋势形成K线始终运行于fast线上方(只做第一次回调)
                # cond_4 = (self.countDrawdowns(days_count) == 1)
                # if cond_4:
                #     self.order = self.buy()
            else:
                pass
        else:
            # self.stopprice = max(0.9*self.data.high[0], self.stopprice)
            cond_1 = self.checkDiv(ago=-1, size=10) and not self.checkDiv(ago=0, size=10)    # 若近五日发散趋势结束，止盈
            cond_2 = self.data.close[0] < self.ma_fast[0]    # 止损
            if (cond_1 or cond_2):
                self.close()


if __name__ == '__main__':
    code_list = ['600088', '000423', '603013', '600612', '600707', '603696', '600572', '603088', '002173', '603990', '000723', '600532', '600499', '002364', '603311', '002966', '600569', '002424', '600792', '603893', '600876', '603488', '603639', '000851', '600668', '000034', '601100', '002699', '603970', '000823', '002248', '600444', '002692', '600368', '600608', '603027', '603305', '000426', '000078', '000963', '600012', '002428', '603698', '000883', '603399', '600463', '603818', '000736', '002907', '600076', '002564', '600738', '600380', '002288', '002009', '000509', '002092', '002408', '002698', '600586', '002795', '600308', '600798', '002091', '002014', '600747', '600099', '002676', '603348', '600789', '600745', '002338', '002660', '600626', '002865', '600637', '603880', '600061', '600897', '000050', '002937', '601233', '002971', '002182', '000650', '600161', '600279', '002712', '603618', '002779', '002777', '002678', '603656', '002623', '600984', '603519', '601101', '002631', '603799', '000759']
    total_profit = 0
    total_loss = 0
    win_num = 0
    loss_num = 0
    # code_list = ['603111']
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
    print('Overall average profit: %.2f' % (overall_average_profit))
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