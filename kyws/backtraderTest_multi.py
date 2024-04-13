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
    print('Getting  %s ...' % code)
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
        self.inds = dict()
        self.orders = dict()
        for i, d in enumerate(self.datas):
            self.inds[d] = dict()
            self.inds[d]['ma_fast'] = bt.ind.SMA(d.close, period = self.params.fast_param)
            self.inds[d]['ma_month'] = bt.ind.SMA(d.close, period = self.params.month_param)
            self.inds[d]['ma_quarter'] = bt.ind.SMA(d.close, period = self.params.quarter_param)
            self.inds[d]['ma_year'] = bt.ind.SMA(d.close, period = self.params.year_param)
            self.orders[d] = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('%s  BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % (order.data._name, order.executed.price, order.executed.value, order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                pass
                self.log('%s  SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % (order.data._name, order.executed.price, order.executed.value, order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('%s Order Canceled/Margin/Rejected' % order.data._name)

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        # self.log('%s  OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.data._name, trade.pnl, trade.pnlcomm))

    # 从当前点向前寻找趋势首日
    def findDDay(self, data):
        for i in range(len(self) - self.params.year_param + 1):    # 从第self.params.year_param日开始才有年线
            if (self.inds[data]['ma_fast'][-i] > self.inds[data]['ma_month'][-i] > self.inds[data]['ma_quarter'][-i]):
                continue
            # cond_1 = (self.inds[d]['ma_month'][-i] - self.inds[d]['ma_quarter'][-i]) > (self.inds[d]['ma_month'][-i-1] - self.inds[d]['ma_quarter'][-i-1])
            # cond_2 = (self.inds[d]['ma_quarter'][-i] - self.inds[d]['ma_year'][-i]) > (self.inds[d]['ma_quarter'][-i-1] - self.inds[d]['ma_year'][-i-1])
            # if (self.inds[d]['ma_month'][-i] < self.inds[d]['ma_quarter'][-i]):    # 月线上穿季度线，不再向前找
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
                cond_1 = self.data.close[-i] < self.inds[d]['ma_fast'][-i]    # 当日收盘低于fast线
                cond_2 = min(pd.Series(self.data.close.get(ago=-i-1, size=5)) - pd.Series(self.inds[d]['ma_fast'].get(ago=-i-1, size=5))) >= 0    # 前5日收盘均高于fast线
                if cond_1 and cond_2:
                    drawdowns += 1
        return drawdowns

    # 计算本次回撤是趋势形成以来的第几次回撤
    def findDrawdownDay(self, data, days):
        ago_days = 0
        if days <= 5:
            ago_days = 0
        else:
            for i in range(days-5):
                cond_1 = data.close[-i] < self.inds[data]['ma_fast'][-i]    # 当日收盘低于fast线
                cond_2 = min(pd.Series(data.close.get(ago=-i-1, size=5)) - pd.Series(self.inds[data]['ma_fast'].get(ago=-i-1, size=5))) >= 0    # 前5日收盘均高于fast线
                if cond_1 and cond_2:
                    ago_days = i+1
                    break
        return ago_days

    # 检查均线发散条件
    def checkDiv(self, data, ago=0, size=5):
        fast_minus_month = pd.Series(self.inds[data]['ma_fast'].get(ago=ago, size=size)) - pd.Series(self.inds[data]['ma_month'].get(ago=ago, size=size))
        cond_1 = fast_minus_month.equals(fast_minus_month.sort_values())
        month_minus_quarter = pd.Series(self.inds[data]['ma_month'].get(ago=ago, size=size)) - pd.Series(self.inds[data]['ma_quarter'].get(ago=ago, size=size))
        cond_2 = month_minus_quarter.equals(month_minus_quarter.sort_values())
        quarter_minus_year = pd.Series(self.inds[data]['ma_quarter'].get(ago=ago, size=size)) - pd.Series(self.inds[data]['ma_year'].get(ago=ago, size=size))
        cond_3 = quarter_minus_year.equals(quarter_minus_year.sort_values())
        if (cond_1 and cond_2 and cond_3):
            return True
        else:
            return False


    def next(self):
        for i, d in enumerate(self.datas):
            # Check if an order is pending ... if yes, we cannot send a 2nd one
            # if self.order.get(d, None):
            #     return

            pos = self.getposition(d).size
            if not pos:
                cond_1_1 = min(pd.Series(self.inds[d]['ma_fast'].get(size=10)) - pd.Series(self.inds[d]['ma_month'].get(size=10))) > 0    # fast线连续10日高于月线
                # cond_1_2 = min(pd.Series(self.inds[d]['ma_month'].get(size=5)) - pd.Series(self.inds[d]['ma_quarter'].get(size=5))) > 0    # 月线连续5日高于季度线
                trend_days = self.findDDay(d)
                ago_days = self.findDrawdownDay(d, trend_days)
                month_minus_quarter = pd.Series(self.inds[d]['ma_month'].get(ago=ago_days, size=9)) - pd.Series(self.inds[d]['ma_quarter'].get(ago=ago_days, size=9))
                cond_1_2 = month_minus_quarter.equals(month_minus_quarter.sort_values())
                cond_1_3 = min(pd.Series(self.inds[d]['ma_quarter'].get(size=3)) - pd.Series(self.inds[d]['ma_year'].get(size=3))) > 0    # 季度线连续3日高于年线
                cond_1 = cond_1_1 and cond_1_2 and cond_1_3
                cond_2 = (d.close[0] > self.inds[d]['ma_fast'][0]) and (self.inds[d]['ma_fast'][-1] > d.close[-1] > self.inds[d]['ma_quarter'][-1])    # 收盘价突破fast线
                cond_3 = d.close[0] > d.open[0]    # 当日收红
                cond_4 = len(d) < d.buflen() - 1    # 仅仅出于统计方便考虑，回测时间段内最后一根k线不买入
                if (cond_1 and cond_2 and cond_3 and cond_4):
                    # print(d.datetime.date())
                    # print(d._name)
                    self.orders[d] = self.buy(data=d)
                else:
                    pass
            else:
                cond_1 = self.checkDiv(data=d, ago=-1, size=10) and not self.checkDiv(data=d, ago=0, size=10)    # 若近五日发散趋势结束，止盈
                cond_2 = d.close[0] < self.inds[d]['ma_fast'][0]    # 止损
                cond_3 = (len(d) == (d.buflen() - 1))    # 倒数第二日若还有持仓，则在最后一日平仓，便于后续统计
                if (cond_1 or cond_2 or cond_3):
                    self.orders[d] = self.close(data=d)


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
    code_list = ['002416', '002188', '000729', '601011', '600692', '000407', '002349', '002845', '601969', '002153', '600077', '002538', '002699', '601001', '600459', '603808', '002861', '002719', '600428', '002226', '000590', '002030', '002606', '600396', '603716', '603778', '002839', '600019', '002394', '600814', '601016', '002269', '600486', '601988', '603890', '600519', '002800', '603979', '600153', '002233', '600518', '001965', '000037', '603928', '000761', '600072', '603477', '603042', '600291', '600312', '002697', '002126', '000536', '000989', '600305', '600661', '603268', '600491', '000719', '002524', '603127', '002909', '603456', '000677', '600800', '603586', '603707', '000505', '603533', '601599', '603987', '000683', '600197', '002930', '002694', '002587', '002322', '600874', '600503', '600035', '603990', '603912', '600722', '002435', '000796', '000415', '002507', '002581', '002523', '002547', '002672', '600805', '600309', '600466', '002020', '603709', '600828', '600227', '000905', '600036', '600573', '600698', '002082', '002161', '603383', '601388', '603101', '603286', '600262', '603023', '002537', '600311', '002851', '002636', '601880', '002827', '600633', '603316', '002334', '002224', '600908', '603358', '002692', '603129', '600418', '002801', '600889', '002602', '600797', '002788', '002755', '600546', '600969', '600328', '002841', '002060', '002585', '603757', '000785', '603777', '603717', '600582', '600630', '002045', '600483', '603768', '600099', '600628', '600158', '603393', '002377', '601789', '600767', '600389', '603535', '600816', '603059', '603900', '000516', '600836', '002819', '600208', '002282', '603882', '600277', '600986', '000025', '002278', '000831', '600398', '600829', '603729', '600897', '600812', '000595', '002407', '002880', '600020', '600558', '002368', '600156', '601566', '002428', '600271', '603887', '000812', '002931', '600515', '603616', '002146', '002162', '600061', '000552', '600719', '000949', '002430', '002508', '000537', '600306', '600385', '002708', '603579', '000858', '600526', '002347', '600894', '603712', '000972', '600560', '603128', '600083', '601038', '603166', '603676', '601200', '600846', '002818', '002753', '603809', '603076', '002033', '600784', '603968', '600370', '002462', '002432', '603703', '600873', '002164', '002532', '603113', '601231', '600853', '600754', '002201', '000679', '600506', '000758', '600726', '000965', '600269', '603988', '002053', '002519', '601368', '002583', '600629', '601900', '600272', '603186', '002869', '600429', '600753', '600993', '600105', '002370', '000780', '603628', '002304', '600129', '000911', '002336', '000401', '600053', '002087', '002777', '600127', '603869', '603345', '002382', '601311', '002009', '603536', '600663', '601998', '002741', '000078', '002015', '000428', '002576', '600392', '600960', '002688', '600807', '600734', '603737', '000063', '600425', '000685', '600455', '002723', '002314', '000788', '600313', '002534', '601858', '002792', '600098', '000682']
    # code_list = ['000031']
    # code_list = getCodeList(start_date, end_date)

    cerebro = bt.Cerebro()
    for code in code_list:
        stock_data = get_data(code, start_date, end_date)
        data = bt.feeds.PandasData(dataname=stock_data)
        data.plotinfo.plot = False
        cerebro.adddata(data, name=code)
    cerebro.addstrategy(SimpleStrategy)
    # # cerebro.optstrategy(SingleEMAStrategy,trend_param=range(600,700,10))
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer,percents=10)

    # Analyzer
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

    thestrats = cerebro.run()
    thestrat = thestrats[0]
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.plot(style='candle')







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