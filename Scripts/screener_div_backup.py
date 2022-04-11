import smtplib
import requests
import time
import json
import random
import threading
import akshare as ak
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
    url = 'https://xueqiu.com/u/3069973870#/stock'
    try_times = 0
    my_list = []
    while (try_times < 5) and (len(my_list) == 0):
        try:
            stock_list = []
            driver.get(url)
            table = driver.find_element_by_css_selector('#app > div.container.profiles__main__container > div.profiles__main > table')
            results = table.find_elements_by_tag_name('tr')[1:]    # 第一项是表头
            for each in results:
                infos = each.find_element_by_tag_name('td')
                stock_symbol = infos.find_element_by_tag_name('a').get_attribute('data-analytics-data')
                stock_code = stock_symbol[-8:-2]
                # print(stock_code)
                my_list.append(stock_code)
        except Exception as e:
            # print(e)
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
    rising_limited_stocks = ak.stock_zt_pool_em(today)['代码'].to_list()
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
    mail_username = 'xxxxxxxxxxx@163.com'
    mail_pw = 'xxxxxxxxxxx'
    mail_recv = ['xxxxxxxxxxx@yandex.com']
    message = MIMEText(mail_content,'plain','utf-8')
    message['Subject'] = subject
    message['From'] = 'xxxxxxxxxxx@163.com'
    message['To'] = mail_recv[0]
    smtpObj = smtplib.SMTP_SSL(mail_host,465)
    smtpObj.login(mail_username,mail_pw)
    smtpObj.sendmail(mail_username,mail_recv[0],message.as_string())
    smtpObj.quit()

class Alchemist(object):

    def __init__(self, code, end_date):
        self.fast_line_para = 10
        self.month_line_para = 20
        self.main_line_para = 60
        self.half_year_line_para = 125
        self.year_line_para = 250
        self.code = code
        self.start_date = '20180101'
        self.end_date = end_date

    # 获取数据
    def getData(self):
        try:
            self.hist_data = ak.stock_zh_a_hist(symbol=self.code, period='daily', start_date=self.start_date, end_date=self.end_date, adjust='hfq')
            if self.hist_data.shape[0] < 2*250:    # 忽略上市时间太短的个股
                return 'too young'
            else:
                self.fast_line = self.hist_data['收盘'].rolling(self.fast_line_para).mean()
                self.month_line = self.hist_data['收盘'].rolling(self.month_line_para).mean()
                self.main_line = self.hist_data['收盘'].rolling(self.main_line_para).mean()
                self.year_line = self.hist_data['收盘'].rolling(self.year_line_para).mean()
                return 'success'
        except Exception as e:
            print(e)
            print(self.code)
            return 'fail'

    # 检查均线发散条件
    def checkDiv(self):
        cond_1 = (self.fast_line[-5:] - self.month_line[-5:]).equals((self.fast_line[-5:] - self.month_line[-5:]).sort_values())
        cond_2 = (self.month_line[-5:] - self.main_line[-5:]).equals((self.month_line[-5:] - self.main_line[-5:]).sort_values())
        cond_3 = (self.main_line[-5:] - self.year_line[-5:]).equals((self.main_line[-5:] - self.year_line[-5:]).sort_values())
        if (cond_1 and cond_2 and cond_3):
            return True
        else:
            return False

    # 检查均线发散趋势是否改变，用于判断顶部
    def checkNotDiv(self):
        cond_1 = not (self.fast_line[-6:] - self.month_line[-6:]).equals((self.fast_line[-6:] - self.month_line[-6:]).sort_values())
        cond_2 = not (self.month_line[-6:] - self.main_line[-6:]).equals((self.month_line[-6:] - self.main_line[-6:]).sort_values())
        cond_3 = not (self.main_line[-6:] - self.year_line[-6:]).equals((self.main_line[-6:] - self.year_line[-6:]).sort_values())
        if (cond_1 or cond_2 or cond_3):
            return True
        else:
            return False

    # 检查买入条件
    def checkBuy(self):
        data_res = self.getData()
        print(data_res)
        if data_res == 'success':
            div_cond = self.checkDiv()
            cond_1 = 1.1*self.year_line.values[-1] > self.hist_data['收盘'].values[-1] > self.year_line.values[-1]    # 收盘价在年线上方不远
            # cond_1 = 1.13*max(self.main_line.values[-1], self.year_line.values[-1]) > self.hist_data['close'].values[-1] > max(self.main_line.values[-1], self.year_line.values[-1])
            cond_2 = max(self.hist_data['最低'].values[-10:] - self.hist_data['最高'].values[-11:-1]) <= 0    # 最近十日无向上跳空
            max_line = max(self.fast_line.values[-1], self.month_line.values[-1], self.main_line.values[-1], self.year_line.values[-1])
            min_line = min(self.fast_line.values[-1], self.month_line.values[-1], self.main_line.values[-1], self.year_line.values[-1])
            cond_3 = 0.85*max_line < min_line
            cond_4 = self.main_line[-6:].equals(self.main_line[-6:].sort_values())    # 60日线近6日处于上升趋势
            if (div_cond and cond_1 and cond_2 and cond_3 and cond_4):
                return True
            else:
                return False
        else:
            return False

    def checkSell(self):
        data_res = self.getData()
        if data_res == 'success':
            div_cond = self.checkDiv()
            not_div_cond = self.checkNotDiv()
            rise_range_cond = self.hist_data['收盘'].values[-1] > 1.2*self.year_line.values[-1]
            if (div_cond and not_div_cond and rise_range_cond):
                return True
            else:
                return False
        else:
            return False


def findBuy(all_stock_dict, code, end_date):
    acm = Alchemist(code, end_date)
    res = acm.checkBuy()
    if res:
        lock.acquire()
        stock_watch_dict[code] = all_stock_dict[code]
        lock.release()
        # print(code + '    ' + all_stock_dict[code] + '    ' + end_date + '\n')
    else:
        pass

def findWarning(all_stock_dict, code, end_date):
    acm = Alchemist(code, end_date)
    res = acm.checkSell()
    if res:
        lock.acquire()
        stock_warning_dict[code] = all_stock_dict[code]
        lock.release()
        # print(code + '    ' + all_stock_dict[code] + '    ' + end_date + '\n')
    else:
        pass


all_stock = ak.stock_zh_a_spot_em()
all_stock_dict = all_stock.set_index(['代码'])['名称'].to_dict()
code_list = sorted(list(all_stock_dict.keys()), key=int)
end_date = dt.datetime.today().strftime('%Y%m%d')
stock_watch_dict = {}
stock_warning_dict = {}
watch_list_now = get_favo_list()
lock = threading.Lock()

for code in code_list:
    t = threading.Thread(target=findBuy, args=(all_stock_dict, code, end_date))
    t.start()
    time.sleep(0.15)

email_content_str = 'Watch List:\n'
for key,value in stock_watch_dict.items():
    email_content_str += (key+'\t'+value+'\n')

try:
    for code in watch_list_now:
        t = threading.Thread(target=findWarning, args=(all_stock_dict, code, end_date))
        t.start()
        time.sleep(0.15)
    email_content_str += '\n\nWarning List:\n'
    for key,value in stock_warning_dict.items():
        email_content_str += (key+'\t'+value+'\n')

    concepts_today = get_concepts_freq()
    email_content_str += '\n\nConcepts:\n'
    for concept in concepts_today:
        email_content_str += (concept[0]+'\t'+str(concept[1])+'\n')
except Exception as e:
    print(e)
finally:
    sendMail(email_content_str)