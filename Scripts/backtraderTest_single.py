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
            cond_4 = len(self.data) < self.data.buflen() - 1    # 仅仅出于统计方便考虑，回测时间段内最后一根k线不买入
            if (cond_1 and cond_2 and cond_3 and cond_4):
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
            cond_3 = (len(self.data) == (self.data.buflen() - 1))    # 倒数第二日若还有持仓，则在最后一日平仓，便于后续统计
            if (cond_1 or cond_2 or cond_3):
                self.close()


# 获取符合条件的全部股票代码
def getCodeList(start_date, end_date):
    all_stock = ak.stock_zh_a_spot_em()
    all_stock_dict = all_stock.set_index(['代码'])['名称'].to_dict()
    all_code_list = list(all_stock_dict.keys())
    code_selected = []
    for code in all_code_list:
        try:
            hist_data = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date, adjust='hfq')
        except:
            continue
        if (hist_data.shape[0] > 2*250) and (code[:2] not in ['30', '68']) and (code[:1] not in ['4', '8']):
            code_selected.append(code)
            print(code + '    ' + all_stock_dict[code])
        else:
            pass
        time.sleep(0.12)
    return code_selected


if __name__ == '__main__':
    start_date = '20170610'
    end_date = '20220610'
    total_profit = 0
    total_loss = 0
    win_num = 0
    loss_num = 0
    trade_len = 0
    # code_list = ['000031', '600516', '601880', '002695', '603915', '000546', '000402', '002389', '600688', '000709', '000830', '002410', '600103', '600283', '601375', '603665', '002349', '002299', '000533', '600190', '600238', '600143', '000738', '000802', '601811', '603811', '600926', '601908', '002625', '600075', '002920', '603039', '002840', '603217', '600893', '600126', '600666', '000420', '002466', '600297', '002339', '002181', '603169', '600708', '601211', '600980', '600491', '002266', '000692', '002722', '600748', '603290', '600105', '601163', '002595', '600309', '000555', '002955', '002336', '600277', '603348', '603108', '002060', '002026', '600860', '000020', '002843', '601228', '000407', '600346', '603458', '002631', '002681', '600936', '600376', '600337', '601198', '002515', '000926', '000733', '000548', '002478', '002388', '603221', '002696', '002215', '002694', '600681', '000921', '002206', '002197', '603010', '601789', '000766', '002793', '000852', '603012', '002690', '603126', '600125']
    # code_list = ['002640']
    # code_list = getCodeList(start_date, end_date)
    with open('./code_list.json', 'r') as f:
        code_list = json.load(f)
    for code in code_list:
        stock_data = get_data(code, start_date, end_date)
        # print(stock_data.head(600).to_string())
        data = bt.feeds.PandasData(dataname=stock_data)
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(SimpleStrategy)
        # # cerebro.optstrategy(SingleEMAStrategy,trend_param=range(600,700,10))
        cerebro.broker.setcash(10000)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addsizer(bt.sizers.PercentSizer,percents=90)

        # Analyzer
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

        thestrats = cerebro.run()
        thestrat = thestrats[0]
        print(code + '  Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
        if cerebro.broker.getvalue() != 10000:
            win_num += thestrat.analyzers.tradeanalyzer.get_analysis().won.total
            loss_num += thestrat.analyzers.tradeanalyzer.get_analysis().lost.total
            trade_len += thestrat.analyzers.tradeanalyzer.get_analysis().len.total
            if cerebro.broker.getvalue() > 10000:
                total_profit += (cerebro.broker.getvalue() - 10000)
            elif cerebro.broker.getvalue() < 10000:
                total_loss += (cerebro.broker.getvalue() - 10000)
        else:
            pass

        # cerebro.plot(style='candle')

    average_profit = total_profit/win_num
    average_loss = total_loss/loss_num
    overall_average_profit = (total_profit + total_loss)/(win_num + loss_num)
    win_rate = win_num/(win_num + loss_num)
    average_trade_length = trade_len/(win_num + loss_num)
    print('Total profit: %.2f' % total_profit)
    print('Average profit: %.2f' % (average_profit))
    print('Average loss: %.2f' % (average_loss))
    print('Overall average profit: %.2f' % (overall_average_profit))
    print('Win rate: %.2f' % (win_rate))
    print('Decision value: %.2f' % (-average_profit/average_loss*win_rate))
    print('Total trade times: %d' % (win_num+loss_num))
    print('Average trade length: %.2f' % average_trade_length)







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