import tushare as ts
import numpy as np
import pandas as pd
import smtplib
from email.mime.text import MIMEText


# send result via email
def sendMail(mail_content,subject="A share"):
    mail_host = 'smtp.163.com'
    mail_username = 'xx@163.com'
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

fast_line_para = 10
main_line_para = 60
half_year_line_para = 125
year_line_para = 250
ts.set_token('')
pro = ts.pro_api('')
all_stock = pro.stock_basic()
all_stock_dict = all_stock.set_index(['ts_code'])['name'].to_dict()
code_list = list(all_stock_dict.keys())
star_stock_dict_1 = {}
star_stock_dict_2 = {}
# code_list = ['000001.SZ']
for code in code_list:
    try:
        hist_data = ts.pro_bar(ts_code=code, start_date='20190101',adj='qfq')
        # hist_data = ts.pro_bar(ts_code=code, start_date='20190101',end_date='20211201',adj='qfq')
        if hist_data.shape[0] < 2*year_line_para:
            continue
        else:
            hist_data = hist_data.sort_values('trade_date')
            fast_line = hist_data['close'].rolling(fast_line_para).mean()
            main_line = hist_data['close'].rolling(main_line_para).mean()
            year_line = hist_data['close'].rolling(year_line_para).mean()
            ema_main_line = hist_data['close'].ewm(span=main_line_para,adjust=False).mean()
            ema_half_year_line = hist_data['close'].ewm(span=half_year_line_para,adjust=False).mean()
            ema_year_line = hist_data['close'].ewm(span=year_line_para,adjust=False).mean()

            cond_1 = min(year_line[-60:-1] - hist_data['close'][-60:-1]) >= 0    # 年线压制
            # cond_2 = year_line.values[-1] - hist_data['close'].values[-1] < 0    # 突破年线
            cond_2 = min(year_line[-60:] - main_line[-60:]) >= 0    # 年线高于均线
            cond_3 = hist_data['close'].values[-1] > main_line.values[-1] > 0.95*hist_data['close'].values[-1]    # 当日收盘价与60日线价差不超过5%
            cond_4 = hist_data['close'].values[-1] > fast_line.values[-1]    # 当日收盘价高于十日线
            cond_5 = (main_line[-5:] == main_line[-5:].sort_values)    # 60日线处于上升趋势
            cond_6 = max(hist_data['close'][-350:]) > 1.5*hist_data['close'].values[-1]    # 最近一年半最高收盘价高于当日收盘价至少50%(充足上涨空间)

            cond_7 = min(ema_year_line[-60:] - ema_half_year_line[-60:]) > 0
            cond_8 = min(ema_half_year_line[-60:] - ema_main_line[-60:]) > 0    # 年线、半年线、60日线空头排列
            cond_9 = max(hist_data['low'][-5:] - ema_year_line[-5:]) > 0    # 近五日曾完全站上年线
            cond_10 = hist_data['close'].values[-2] > ema_year_line.values[-2]    # 昨日收于年线上方
            cond_11 = ema_year_line.values[-1] > hist_data['close'].values[-1] > ema_main_line.values[-1]    # 回踩年线
            cond_12 = hist_data['close'].values[-1] > ema_main_line.values[-1] > 0.95*hist_data['close'].values[-1]    # 当日收盘价与60日线价差不超过5%
            if (cond_1 and cond_2 and cond_3 and cond_4 and cond_5 and cond_6):
                # print(code+'   '+all_stock_dict[code])
                star_stock_dict_1[code]=all_stock_dict[code]
            else:
                pass
            if (cond_7 and cond_8 and cond_9 and cond_10 and cond_11 and cond_12):
                # print(code+'   '+all_stock_dict[code])
                star_stock_dict_2[code]=all_stock_dict[code]
            else:
                pass
    except:
        continue

star_stock_str = 'Strategy 1:\n'
for key,value in star_stock_dict_1.items():
    star_stock_str += (key+'\t'+value+'\n')
star_stock_str += '\n\nStrategy 2:\n'
for key,value in star_stock_dict_2.items():
    star_stock_str += (key+'\t'+value+'\n')
sendMail(star_stock_str)