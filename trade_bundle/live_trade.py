import requests
import time
import datetime
import json
import pandas as pd
import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

# 订阅的标的列表
stock_list = []
session = None
cookies = None
headers = {
	'Accept':'*/*',
	'Origin':'https://xueqiu.com',
	'Referer':'https://xueqiu.com/S/SH600519',
	'Sec-Fetch-Mode':'cors',
	'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
}

NAN_DT = datetime.datetime(2200, 1, 1)

class _Global(object):

    def __init__(self, **kwargs):
        
        for name, value in kwargs.items():
            setattr(self, name, value)

# 通用对象转化
class _Context(object):

    def __init__(self, **kwargs):
        
        for name, value in kwargs.items():
            setattr(self, name, value)

class Tick(object):
	def __init__(self, security, tick):
		self._security = parse_xq_code(security)
		self._tick = tick

	@property
	def code(self):
		return self._security

	@property
	def time(self):
		try:
			return self._tick['time']
		except:
			return NAN_DT

	@property
	def current(self):
		try:
			return self._tick['current']
		except:
			return np.nan

	@property
	def high(self):
		try:
			return self._tick['high']
		except:
			return np.nan

	@property
	def low(self):
		try:
			return self._tick['low']
		except:
			return np.nan

	@property
	def trade_volume(self):
		try:
			return self._tick['trade_volume']
		except:
			return np.nan

	@property
	def volume(self):
		try:
			return self._tick['volume']
		except:
			return np.nan

	@property
	def money(self):
		try:
			return self._tick['money']
		except:
			return np.nan

# 通用对象转化
class CurrentDict(object):

	def __init__(self, **kwargs):
		
		for name, value in kwargs.items():
			setattr(self, name, value)

# 当前行情对象
class _CurrentDic(dict):

	def __init__(self, date):
		pass

	def __missing__(self, code):
		info = _global['session'].get('https://stock.xueqiu.com/v5/stock/quote.json?extend=detail&symbol=' + parse_code(code), cookies = _global['cookies'], headers = headers).json()
		quote = info['data']['quote']
		stock = quote['symbol']
		result = {
			'name': quote['name'],
			'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(quote['timestamp'] / 1000)),
			'current': quote['current'],
			'high': quote['high'],
			'low': quote['low'],
			'volume': quote['volume'],
			'money': quote['amount'],
			'day_open': quote['open'],
			'high_limit': quote['limit_up'],
			'low_limit': quote['limit_down'],
			'industry_code': quote['type'],
			'is_st': quote['status'] == 2
		}

		return parse(result)

# 初始化实时行情模块
# 主要工作是 初始化爬虫cookie 初始化tick定时器 完善全局对象
def init_current_bundle(initialize, before_trading_start, after_trading_end, handle_tick):
	_global['initialize'] = initialize
	_global['before_trading_start'] = before_trading_start
	_global['after_trading_end'] = after_trading_end
	_global['handle_tick'] = handle_tick
	cookies = get_cookie()

	# 执行初始化函数
	initialize(_global['context'])

	# 初始化tick定时器
	init_schedudler()

# 创建定时器 
# 完成开盘 收盘 盘中3秒批量查询一次最新tick数据 等默认事件
def init_schedudler():
	schedudler = BlockingScheduler()
	schedudler.add_job(func = _global['before_trading_start'], args = [_global['context']], trigger = 'cron', hour = 9, minute = 9, day_of_week = 'mon-fri')
	schedudler.add_job(func = _global['after_trading_end'], args = [_global['context']], trigger = 'cron', hour = 15, minute=30, day_of_week = 'mon-fri')
	schedudler.add_job(_get_current_tick, 'cron', second = '*/3')
	schedudler.start()

def get_cookie():
	cookies = requests.cookies.RequestsCookieJar()
	_global['session'] = requests.session()
	r = _global['session'].get('https://xueqiu.com/k?q=SZ131810', headers = headers)
	_global['cookies'] = r.cookies
	return cookies

# 抓取当日历史tick数据
def get_ticks(security, end_dt, count, start_dt = None):
	print('### 自定义 get_ticks ###')
	result = []

	# 大于100取东方财富的 稍后实现
	if count > 100:
		pass
	else:
		info = _global['session'].get('https://stock.xueqiu.com/v5/stock/history/trade.json?symbol=' + parse_code(security) + '&count=' + str(count), cookies = _global['cookies'], headers = headers).json()
		ticks = info['data']['items']

		for tick in ticks:
			result.append({
				'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tick['timestamp'] / 1000)),
				'current': tick['current'],
				'trade_volume': tick['trade_volume'],
			})

	return result

# 获取最新tick数据
def get_current_tick(stock, df = False):
	info = _global['session'].get('https://stock.xueqiu.com/v5/stock/realtime/quotec.json?symbol=' + parse_code(stock), cookies = _global['cookies'], headers = headers).json()
	quote = info['data'][0]
	stock = quote['symbol']
	result = {
		'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(quote['timestamp'] / 1000)),
		'current': quote['current'],
		'high': quote['high'],
		'low': quote['low'],
		'trade_volume': quote['trade_volume'],
		'volume': quote['volume'],
		'money': quote['amount']
	}

	return Tick(stock, result)

# 获取当日最新数据 包含涨停跌停等
def get_current_data():
	print('### 自定义 get_current_data ###')
	current = _CurrentDic({})
	return current

# 获取最新tick数据
def _get_current_tick():
	stocks = []

	if len(stock_list):

		for stock in stock_list:
			stocks.append(parse_code(stock))

		info = _global['session'].get('https://stock.xueqiu.com/v5/stock/realtime/quotec.json?symbol=' + ','.join(stocks), cookies = _global['cookies'], headers = headers).json()
		quotes = info['data']

		for quote in quotes:
			stock = quote['symbol']
			result = {
				'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(quote['timestamp'] / 1000)),
				'current': quote['current'],
				'high': quote['high'],
				'low': quote['low'],
				'trade_volume': quote['trade_volume'],
				'volume': quote['volume'],
				'money': quote['amount']
			}
			_global['handle_tick'](_global['context'], Tick(stock, result))

def parse_code(code):
	
	if code.endswith('XSHE'):
		return 'SZ' + code.split('.')[0]
	elif code.endswith('XSHG'):
		return 'SH' + code.split('.')[0]

def parse_xq_code(code):
	
	if code.startswith('SZ'):
		return code[2:8] + '.XSHE'
	elif code.startswith('SH'):
		return code[2:8] + '.XSHG'

# 要暴露的函数
def subscribe(security, frequency):
	print('### 自定义 subscribe ###')

	# 加入队列
	stock_list.append(security)
	print('添加标的到队列 => ', security)
	# print('当前订阅的标的队列 => ', stock_list)

# 取消订阅标的的 tick 事件
def unsubcribe(security, frequency):
	print('### 自定义 unsubcribe ###')

	if security in stock_list:
		stock_list.remove(security)

# 取消订阅所有 tick 事件
def unsubscribe_all():
	print('### 自定义 unsubscribe_all ###')
	stock_list = []

# 定时执行任务
def run_daily(event, time):
	_time = time.split(':')
	hour = int(_time[0])
	minute = int(_time[1])
	schedudler = BackgroundScheduler()
	schedudler.add_job(func = event, args = [_global['context']], trigger = 'cron', hour = hour, minute = minute, day_of_week = 'mon-fri')
	schedudler.start()

## 格式化返回的数据
def parse(data):
	result = json.loads(json.dumps(data), object_hook=lambda d: CurrentDict(**d))
	return result

## 格式化返回的数据
def _parse_global(data):
    result = json.loads(json.dumps(data), object_hook=lambda d: _Global(**d))
    return result

## 格式化返回的数据
def _parse_context(data):
    result = json.loads(json.dumps(data), object_hook=lambda d: _Context(**d))
    return result

# 暴露的全局变量
g = _parse_global({})
context = _parse_context({})

# 保存一些内容
_global = {
	'session': None,
	'cookies': None,
	'context': context,
	'g': g
}