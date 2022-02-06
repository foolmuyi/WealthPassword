import smtplib
import requests
import time
import random
import akshare as ak
import tushare as ts
import numpy as np
import pandas as pd
import datetime as dt
from bs4 import BeautifulSoup
from collections import Counter
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.support.ui import Select


# get my favoriates list
def get_favo_list():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('headless')
    driver = webdriver.Chrome(options=chrome_options)
    url = ''   # removed
    try_times = 0
    my_list = []
    while (try_times < 5) and (len(my_list) == 0):
        try:
            stock_list = []
            driver.get(url)
            table = driver.find_element_by_css_selector('#app > div.container.profiles__main__container > div.profiles__main > table')
            results = table.find_elements_by_tag_name('tr')[1:]    # 第一项是表头
            for each in results:
                infos = each.find_elements_by_tag_name('td')
                stock_name = infos[0].text
                my_list.append(stock_name)
        except:
            try_times += 1
    return my_list


# get concepts of each rising limiting stock
def get_concepts(code):
    concepts = []
    url = 'http://ddx.gubit.cn/showbk.php?code='+code
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'lxml')
    bknames = soup.select('#bkdata > div.bkbox.bkbox_w2 > div.bkbox_bd > div > div.bkname')
    for each in bknames:
        concepts.append(each.string)
    return concepts


def get_concepts_freq():
    today = dt.date.today().strftime('%Y%m%d')
    rising_limited_stocks = ak.stock_em_zt_pool(today)['代码'].to_list()
    concept_list = []
    for code in rising_limited_stocks:
        try_times = 0
        while try_times < 5:
            try:
                concepts = get_concepts(code)
                concept_list += concepts
                # print(concepts)
                time.sleep(random.random())
                break
            except Exception as e:
                # print(e)
                continue
    concept_list_res = []
    concept_ignore = ['融资融券', '预盈预增', '大盘', '中盘', '小盘', '富时罗素', 'MSCI中国', '深圳200', '龙虎榜热门', '深证成指', '昨日涨停', '次新股', '百元股', '昨日连板']
    for each in concept_list:
        if each not in concept_ignore:
            concept_list_res.append(each)
    concepts_top_10 = Counter(concept_list_res).most_common(10)
    return concepts_top_10

# send result via email
def sendMail(mail_content,subject="Today's A share chances"):
    mail_host = 'smtp.163.com'
    mail_username = ''    # removed
    mail_pw = ''    # removed
    mail_recv = ['']    # removed
    message = MIMEText(mail_content,'plain','utf-8')
    message['Subject'] = subject
    message['From'] = ''    # removed
    message['To'] = mail_recv[0]
    smtpObj = smtplib.SMTP_SSL(mail_host,465)
    smtpObj.login(mail_username,mail_pw)
    smtpObj.sendmail(mail_username,mail_recv[0],message.as_string())
    smtpObj.quit()

# 策略思路：60日均线长期低于年线，近期处于上升态势（收盘高于10日线，60日线上升），但高于60日线不超过5%（便于止损）


# 选股
fast_line_para = 10
main_line_para = 60
half_year_line_para = 125
year_line_para = 250
ts.set_token('')    # removed
pro = ts.pro_api('')    # removed
all_stock = pro.stock_basic()
all_stock_dict = all_stock.set_index(['ts_code'])['name'].to_dict()
code_list = list(all_stock_dict.keys())
star_stock_dict_1 = {}
star_stock_dict_2 = {}
my_list = get_favo_list()
# code_list = ['000001.SZ']
for code in code_list:
    try:
        hist_data = ts.pro_bar(ts_code=code, start_date='20180101',end_date='20210601',adj='qfq')
        # hist_data = ts.pro_bar(ts_code=code, start_date='20190101',end_date='20211201',adj='qfq')
        if (hist_data.shape[0] < 2*year_line_para) or (all_stock_dict[code] in my_list):    # 忽略上市时间太短和已经在自选列表的
            continue
        else:
            hist_data = hist_data.sort_values('trade_date')
            fast_line = hist_data['close'].rolling(fast_line_para).mean()
            main_line = hist_data['close'].rolling(main_line_para).mean()
            year_line = hist_data['close'].rolling(year_line_para).mean()
            ema_main_line = hist_data['close'].ewm(span=main_line_para,adjust=False).mean()
            ema_half_year_line = hist_data['close'].ewm(span=half_year_line_para,adjust=False).mean()
            ema_year_line = hist_data['close'].ewm(span=year_line_para,adjust=False).mean()

            # cond_1 = min(year_line[-60:-1] - hist_data['close'][-60:-1]) >= 0    # 年线压制
            # cond_2 = year_line.values[-1] - hist_data['close'].values[-1] < 0    # 突破年线
            cond_2 = min(year_line[-60:] - main_line[-60:]) >= 0    # 年线高于均线
            cond_3 = hist_data['close'].values[-1] > main_line.values[-1] > 0.95*hist_data['close'].values[-1]    # 当日收盘价与60日线价差不超过5%
            cond_4 = hist_data['close'].values[-1] > fast_line.values[-1]    # 当日收盘价高于十日线
            cond_5 = main_line[-5:].equals(main_line[-5:].sort_values())    # 60日线处于上升趋势
            cond_6 = max(hist_data['close'][-350:]) > 1.5*hist_data['close'].values[-1]    # 最近一年半最高收盘价高于当日收盘价至少50%(充足上涨空间)

            cond_7 = min(ema_year_line[-60:] - ema_half_year_line[-60:]) > 0
            cond_8 = min(ema_half_year_line[-60:] - ema_main_line[-60:]) > 0    # 年线、半年线、60日线空头排列
            cond_9 = max(hist_data['low'][-5:] - ema_year_line[-5:]) > 0    # 近五日曾完全站上年线
            cond_10 = hist_data['close'].values[-2] > ema_year_line.values[-2]    # 昨日收于年线上方
            cond_11 = ema_year_line.values[-1] > hist_data['close'].values[-1] > ema_main_line.values[-1]    # 回踩年线
            cond_12 = hist_data['close'].values[-1] > ema_main_line.values[-1] > 0.95*hist_data['close'].values[-1]    # 当日收盘价与60日线价差不超过5%
            if (cond_2 and cond_3 and cond_4 and cond_5 and cond_6):
                print('Strategy 1:'+code+'   '+all_stock_dict[code])
                star_stock_dict_1[code]=all_stock_dict[code]
            else:
                pass
            if (cond_7 and cond_8 and cond_9 and cond_10 and cond_11 and cond_12):
                # print('Strategy 2:'+code+'   '+all_stock_dict[code])
                star_stock_dict_2[code]=all_stock_dict[code]
            else:
                pass
    except:
        continue

# star_stock_str = 'Strategy 1:\n'
# for key,value in star_stock_dict_1.items():
#     star_stock_str += (key+'\t'+value+'\n')
# star_stock_str += '\n\nStrategy 2:\n'
# for key,value in star_stock_dict_2.items():
#     star_stock_str += (key+'\t'+value+'\n')
# concepts_today = get_concepts_freq()
# star_stock_str += '\n\nConcepts:\n'
# for concept in concepts_today:
#     star_stock_str += (concept[0]+'\t'+str(concept[1])+'\n')
# sendMail(star_stock_str)