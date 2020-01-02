# 券商客户端自动下单
import pyautogui
import functools
from pywinauto.application import Application

from typing import Type
from trade_order.src.grid_strategy import IGridStrategy
from trade_order.src.grid_strategy import Copy

from trade_order.src.pop_dialog_handler import TradePopDialogHandler
from trade_order.src.pop_dialog_handler import PopDialogHandler

import time
import easyutils

from trade_order.src.client import *
from trade_order.src.ocr import *

class ZTClientTrader():

	grid_strategy: Type[IGridStrategy] = Copy

	@property
	def broker_type(self):
		return "ths"

	@property
	def config(self):
		return self._config

	@property
	def app(self):
		return self._app

	@property
	def main(self):
		return self._main

	def __init__(self):
		self._config = create(self.broker_type)
		self._app = None
		self._main = None

	'''
		获取矩阵内容
	'''
	def _get_grid_data(self, control_id):
		return self.grid_strategy(self).get(control_id)

	'''
		处理复制时产生的验证码
	'''
	def _parse_grid_yzm(self):
		self.wait(0.3)
		self._main = self._app.top_window()
		yzm_control = self._main.children(class_name = "Static")[1]
		input_control = self._main.child_window(class_name = 'Edit')
		code = get_yzm_text(yzm_control)

		## 如果识别长度不为4则重试
		if (len(code) != 4):
			self._main.children(title='取消')[0].click()
			return True
		else:
			input_control.set_text(code)
			self._main.children(title='确定')[0].click()
			self._main = self._app.top_window()
			error_control = self._main.children(class_name = "Static")[2].window_text()

			if error_control == '验证码错误！！':
				self._main.children(title='取消')[0].click()
				return True

	def _switch_left_menus(self, path, sleep=0.2):
		self._main = self._app.top_window()
		self._get_left_menus_handle().get_item(path).click()
		self._app.top_window().type_keys('{F5}')
		self.wait(sleep)

	@functools.lru_cache()
	def _get_left_menus_handle(self):
		while True:
			try:
				handle = self._main.child_window(
					control_id=129, class_name="SysTreeView32"
				)
				# sometime can't find handle ready, must retry
				handle.wait("ready", 2)
				return handle
			# pylint: disable=broad-except
			except Exception:
				pass

	def wait(self, seconds):
		time.sleep(seconds)

	''' 初始化运行交易客户端 '''
	def connect(self, client_path = None):
		self._app = Application().start(client_path)
		self._main = self._app.top_window()

	''' 登录交易客户端 '''
	def login(self, account, password):

		# 选择营业部
		self._main.ComboBox2.select(15)

		## 输入账号
		self._main.children(class_name='Edit')[0].type_keys(account)
		time.sleep(1)

		## 输入密码
		self._main.children(class_name='Edit')[1].type_keys(password)
		time.sleep(1)

		yzm_control = self._main.children(class_name = "Static")[0]

		code = get_yzm_text(yzm_control)

		wins = self._main.children(class_name='Edit')[6]
		wins.type_keys(code)
		self._main.child_window(class_name='Button', title='确定(&Y)').click()

		# 重新赋值
		self._main = self._app.top_window()
		time.sleep(2)

	def refresh(self):
		self._switch_left_menus(["买入[F1]"], sleep=0.05)

	def _get_balance_from_statics(self):
		result = {}
		self._app.top_window().type_keys('{F5}')
		self.wait(0.3)

		for key, control_id in self._config.BALANCE_CONTROL_ID_GROUP.items():
			result[key] = self._main.child_window(
				control_id=control_id, class_name="Static"
			).window_text()
		return result

	''' 查询持仓 [包含资金详情和持仓详情] '''
	def get_position(self):
		self.refresh()
		self._app.top_window().type_keys('{F5}')
		self.wait(0.3)
		self._switch_left_menus(["查询[F4]", "资金股票"])

		''' 获取资金详情 '''
		cash = self._get_balance_from_statics()

		''' 获取持仓 '''
		self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
		isNotYzm = self._parse_grid_yzm()

		if isNotYzm == True:
			self._switch_left_menus(["查询[F4]", "资金股票"])
			self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
			self._parse_grid_yzm()

			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			position = self.grid_strategy(self)._format_grid_data(content)

			result = {
				'cash': cash,
				'position': position
			}

			# 返回持仓的json数据
			return result
		else:

			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			position = self.grid_strategy(self)._format_grid_data(content)

			result = {
				'cash': cash,
				'position': position
			}

			# 返回持仓的json数据
			return result

	''' 查询当日委托 '''
	def today_entrusts(self):
		self._switch_left_menus(["查询[F4]", "当日委托"])
		self.wait(0.1)
		self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
		self.wait(0.1)
		isNotYzm = self._parse_grid_yzm()

		if isNotYzm == True:
			self._switch_left_menus(["查询[F4]", "当日委托"])
			self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
			self._parse_grid_yzm()
		else:

			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			result = self.grid_strategy(self)._format_grid_data(content)

			# 返回持仓的json数据
			return result

	''' 查询当日成交 '''
	def today_trades(self):
		self._switch_left_menus(["查询[F4]", "当日成交"])
		self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
		isNotYzm = self._parse_grid_yzm()

		if isNotYzm == True:
			self._switch_left_menus(["查询[F4]", "当日成交"])
			self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
			self._parse_grid_yzm()
		else:

			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			result = self.grid_strategy(self)._format_grid_data(content)

			# 返回持仓的json数据
			return result

	''' 查询撤单列表 '''
	def cancel_entrusts(self):
		self._app.top_window().type_keys('{F5}')
		self.wait(0.2)
		self.refresh()
		self.wait(0.2)
		self._switch_left_menus(["撤单[F3]"])
		self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
		isNotYzm = self._parse_grid_yzm()

		# 如果验证码识别失败
		if isNotYzm == True:
			self._switch_left_menus(["撤单[F3]"])
			self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
			self._parse_grid_yzm()
		else:

			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			result = self.grid_strategy(self)._format_grid_data(content)
			self._app.top_window().type_keys('{F5}')
			return result

	''' 撤单 '''
	def cancel_entrust(self, entrust_no):
		self._app.top_window().type_keys('{F5}')

		# 获取撤单列表
		for i, entrust in enumerate(self.cancel_entrusts()):

			if entrust[self._config.CANCEL_ENTRUST_ENTRUST_FIELD] == str(entrust_no):
				self._cancel_entrust_by_double_click(i)
				self._app.top_window().type_keys('{F5}')
				return self._handle_pop_dialogs()

		return {"message": "委托单状态错误不能撤单, 该委托单可能已经成交或者已撤"}


	''' 执行撤单操作 '''
	def _cancel_entrust_by_double_click(self, row):
		self.wait(0.3)
		x = self._config.CANCEL_ENTRUST_GRID_LEFT_MARGIN
		y = (
			self._config.CANCEL_ENTRUST_GRID_FIRST_ROW_HEIGHT
			+ self._config.CANCEL_ENTRUST_GRID_ROW_HEIGHT * row
		)

		self._app.top_window().child_window(
			control_id=self._config.COMMON_GRID_CONTROL_ID,
			class_name="CVirtualGridCtrl",
		).double_click(coords=(x, y))

	def _is_exist_pop_dialog(self):
		self.wait(0.1)
		return (
			self._main.wrapper_object()
			!= self._app.top_window().wrapper_object()
		)

	def _get_pop_dialog_title(self):
		return (
			self._app.top_window()
			.child_window(control_id=self._config.POP_DIALOD_TITLE_CONTROL_ID)
			.window_text()
		)

	def _handle_pop_dialogs(
		self, handler_class=PopDialogHandler
	):
		handler = handler_class(self._app)
		while self._is_exist_pop_dialog():
			title = self._get_pop_dialog_title()

			result = handler.handle(title)

			if result:
				return result
		return {"message": "success"}

	def _submit_trade(self):
		time.sleep(0.05)
		self._main.child_window(
			control_id=self._config.TRADE_SUBMIT_CONTROL_ID,
			class_name="Button",
		).click()

	def _set_trade_params(self, security, price, amount):
		code = security[-6:]

		self._type_keys(self._config.TRADE_SECURITY_CONTROL_ID, code)

		# wait security input finish
		self.wait(0.1)

		self._type_keys(
			self._config.TRADE_PRICE_CONTROL_ID,
			easyutils.round_price_by_code(price, code),
		)
		self._type_keys(self._config.TRADE_AMOUNT_CONTROL_ID, str(int(amount)))

	def _type_keys(self, control_id, text):
		self._main.child_window(
			control_id=control_id, class_name="Edit"
		).set_edit_text(text)

	def trade(self, security, price, amount):
		self._set_trade_params(security, price, amount)
		self.wait(0.1)
		self._submit_trade()
		return self._handle_pop_dialogs(
			handler_class=TradePopDialogHandler
		)

	def buy(self, security, price, amount, **kwargs):
		self._switch_left_menus(["买入[F1]"])
		return self.trade(security, price, amount)

	def sell(self, security, price, amount, **kwargs):
		self._switch_left_menus(["卖出[F2]"])
		return self.trade(security, price, amount)

	def market_buy(self, security, amount, ttype=None, **kwargs):
		"""
		市价买入
		:param security: 六位证券代码
		:param amount: 交易数量
		:param ttype: 市价委托类型，默认客户端默认选择，
					 深市可选 ['对手方最优价格', '本方最优价格', '即时成交剩余撤销', '最优五档即时成交剩余 '全额成交或撤销']
					 沪市可选 ['最优五档成交剩余撤销', '最优五档成交剩余转限价']

		:return: {'entrust_no': '委托单号'}
		"""
		self._switch_left_menus(["市价委托", "买入"])
		return self.market_trade(security, amount, ttype)

	def market_sell(self, security, amount, ttype=None, **kwargs):
		"""
		市价卖出
		:param security: 六位证券代码
		:param amount: 交易数量
		:param ttype: 市价委托类型，默认客户端默认选择，
					 深市可选 ['对手方最优价格', '本方最优价格', '即时成交剩余撤销', '最优五档即时成交剩余 '全额成交或撤销']
					 沪市可选 ['最优五档成交剩余撤销', '最优五档成交剩余转限价']

		:return: {'entrust_no': '委托单号'}
		"""
		self._switch_left_menus(["市价委托", "卖出"])

		return self.market_trade(security, amount, ttype)

	def market_trade(self, security, amount, ttype=None, **kwargs):
		"""
		市价交易
		:param security: 六位证券代码
		:param amount: 交易数量
		:param ttype: 市价委托类型，默认客户端默认选择，
					 深市可选 ['对手方最优价格', '本方最优价格', '即时成交剩余撤销', '最优五档即时成交剩余 '全额成交或撤销']
					 沪市可选 ['最优五档成交剩余撤销', '最优五档成交剩余转限价']

		:return: {'entrust_no': '委托单号'}
		"""

		self._set_market_trade_params(security, amount)
		self.wait(0.01)

		if ttype is not None:
			self._set_market_trade_type(ttype)
		self._submit_trade()
		# self.wait(0.3)
		return self._handle_pop_dialogs(
			handler_class=TradePopDialogHandler
		)

	def _set_market_trade_type(self, ttype):
		"""根据选择的市价交易类	型选择对应的下拉选项"""
		selects = self._main.child_window(
			control_id=self._config.TRADE_MARKET_TYPE_CONTROL_ID,
			class_name="ComboBox",
		)
		for i, text in selects.texts():
			# skip 0 index, because 0 index is current select index
			if i == 0:
				continue
			if ttype in text:
				selects.select(i - 1)
				break
		else:
			raise TypeError("不支持对应的市价类型: {}".format(ttype))

	def _set_market_trade_params(self, security, amount):
		code = security[-6:]

		self._type_keys(self._config.TRADE_SECURITY_CONTROL_ID, code)

		# wait security input finish
		self.wait(0.1)

		self._type_keys(self._config.TRADE_AMOUNT_CONTROL_ID, str(int(amount)))

	def auto_ipo(self):
		# self.wait(3)
		self._switch_left_menus(self._config.AUTO_IPO_MENU_PATH)
		self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
		isNotYzm = self._parse_grid_yzm()

		if isNotYzm == True:
			self._switch_left_menus(self._config.AUTO_IPO_MENU_PATH)
			self._get_grid_data(self._config.COMMON_GRID_CONTROL_ID)
			self._parse_grid_yzm()
		else:
			# 解析剪贴板上的数据
			content = self.grid_strategy(self)._get_clipboard_data()
			stock_list = self.grid_strategy(self)._format_grid_data(content)

			if len(stock_list) == 0:
				return {"message": "今日无新股"}
			invalid_list_idx = [
				i for i, v in enumerate(stock_list) if v["申购数量"] <= 0
			]

			if len(stock_list) == len(invalid_list_idx):
				return {"message": "没有发现可以申购的新股"}

			self.wait(0.1)

			for row in invalid_list_idx:
				self._click_grid_by_row(row)
			self.wait(0.1)

			self._click(self._config.AUTO_IPO_BUTTON_CONTROL_ID)
			self.wait(0.1)

			return self._handle_pop_dialogs()

	def _click(self, control_id):
		self._app.top_window().child_window(
			control_id=control_id, class_name="Button"
		).click()

	def _click_grid_by_row(self, row):
		x = self._config.COMMON_GRID_LEFT_MARGIN
		y = (
			self._config.COMMON_GRID_FIRST_ROW_HEIGHT
			+ self._config.COMMON_GRID_ROW_HEIGHT * row
		)
		self._app.top_window().child_window(
			control_id=self._config.COMMON_GRID_CONTROL_ID,
			class_name="CVirtualGridCtrl",
		).click(coords=(x, y))
