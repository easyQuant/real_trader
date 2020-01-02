# 封装一层函数 兼容聚宽的实盘和回测函数调用
from trade_order.src.index import ZhongTaiTrader, X

import requests
import time
import json
from collections import namedtuple

# 实时数据模块 [tick相关函数覆盖]
from trade_bundle.live_trade import get_current_tick

_order_global = {}

# 委托单对象
class RealOrders():

    def __init__(self, value):
        self.value = value
        
    def values(self):
        return self.value

# 初始化实盘模块
def init_trader(g, context, account, password, path):
    print('##### 初始化实盘模块 #####')
    _order_global['trader'] = ZhongTaiTrader()
    _order_global['g'] = g
    _order_global['context'] = context
    print('准备登录资金账号 {}'.format(account))
    run_client(path)
    login(account, password)
    time.sleep(1)
    handle_async_portfolio(True)

# 初始化邮件模块
def send_email(title, context):
    _order_global['trader'].send_email(title, context)

def run_client(path):
    _order_global['trader'].run_client(path)

# 登陆账号
def login(userId, password):
    info = _order_global['trader'].login(userId, password)

# 按数量买入
# stock 600519.XSHG 股票代码
# amount 委托数量
# style MarketOrder 市价 / LimitOrder 限价
def order(stock, amount, price = None):
    style = None
    info = order_type(stock, price, style)
    return order_amount(info.get('security'), amount, info.get('price'), info.get('style'))

# 买入到指定数量
# stock 600519.XSHG 股票代码
# amount 委托数量
# style MarketOrder 市价 / LimitOrder 限价
def order_target(stock, amount, price = None):
    style = None
    info = order_type(stock, price, style)
    security = info.get('security')
    price = info.get('price')
    style = info.get('style')
    amount = order_target_amount(info.get('security'), amount)
    return order_amount(security, amount, price, style)

# 按价值下单
# stock 600519.XSHG 股票代码
# value 下单金额
# amount 委托数量
# style MarketOrder 市价 / LimitOrder 限价
def order_value(stock, value, price = None):
    style = None
    info = order_type(stock, price, style)
    amount = round_amount(value / info.get('price'))
    return order_amount(info.get('security'), amount, info.get('price'), info.get('style'))

# 买入到指定价值
# stock 600519.XSHG 股票代码
# value 买入金额
# amount 委托数量
# style MarketOrder 市价 / LimitOrder 限价
def order_target_value(stock, value, price = None):
    style = None
    info = order_type(stock, price, style)
    amount = round_amount(value / info.get('price'))
    amount = order_target_amount(info.get('security'), amount)
    return order_amount(info.get('security'), amount, info.get('price'), info.get('style'))

# 撤单
# order_id 单号id
def cancel_order(order_id):
    _order_global['trader'].cancel_entrust(order_id)
    handle_after_order()

# 实现一些钩子函数
# TODO: 钩子函数
# 更新实盘账户信息后
def handle_after_async_portfolio():
    _order_global['g'].async_portfolio_flag = False

# TODO: 钩子函数
# 同步实盘账户信息
# is_force 是否强制更新持仓 默认只有下单后调用才会更新
def handle_async_portfolio(is_force = False):
    
    # 如果是强制查询
    if is_force == True:
        _order_global['g'].async_portfolio_flag = True

    if (_order_global['g'].async_portfolio_flag):
        position = _order_global['trader'].position()

        ## 格式化持仓信息然后赋值给portfolio
        positions = parse_positions(position['positions'])
        
        ## 格式化资产信息
        _order_global['context'].portfolio = parse(position['portfolio'])
        _order_global['context'].portfolio.positions = positions
        _order_global['g'].context = _order_global['context']

        # 查询后的钩子
        handle_after_async_portfolio()
    return _order_global['context'].portfolio

# TODO: 钩子函数
# 实盘下单
def handle_order():
    pass

# 更新成交状态 下一个tick同步实盘账户信息
# TODO: 钩子函数
# 实盘下单后
def handle_after_order():
    # print('### 有下单动作 下一个tick进行持仓查询 ### ')
    _order_global['g'].async_portfolio_flag = True

# 获取订单信息
def get_orders():
    return RealOrders(_order_global['trader'].today_entrusts())

# 获取未完成订单
def get_open_orders():
    return RealOrders(_order_global['trader'].cancel_entrusts())

# 获取成交信息
def get_trades():
    return RealOrders(_order_global['trader'].trades())

# 满额打新股
def auto_ipo():
    pass

# 统一委托下单类型
def order_type(stock, price, style):
    security = stock.split('.')[0]

    # 如果不传入价格 同时委托类型为市价 则传当前价格
    if (price == None):
        price = get_current_tick(stock).current
        style = 'MarketOrder'
    else:
        style = 'LimitOrder'

    return {
        'security': security,
        'style': style,
        'price': price
    }

# 根据持仓指定下单数量
def order_target_amount(security, amount):
    # print(_order_global['context'].portfolio.positions)

    if _order_global['trader'].parse_stock_code(security) in _order_global['context'].portfolio.positions:

        # 获取当前持仓
        info = _order_global['context'].portfolio.positions[_order_global['trader'].parse_stock_code(security)]

        # print('info => ', info)

        # 获取持有数量
        total_amount = int(info['total_amount'])
    else:
        total_amount = 0
    
    # 如果预期数量等于0 则清仓
    if amount <= 0:
        amount = 0 - total_amount
    
    elif (amount > total_amount) or (amount < total_amount):
        amount = amount - total_amount

    # 如果预期数量等于持有数量 则忽略
    elif amount == total_amount:
        amount = 0

    return amount

# 底层委托函数
def order_amount(security, amount, price, style):
    amount = revision_amount(security, _order_global['context'].portfolio.available_cash, amount, price)
    result = {}

    if amount == 0:
        result = {
            'message': '预期数量等于持有数量 忽略本次下单'
        }
        print('风控函数 标的: {} 回报信息: {}'.format(security, result['message']))
    else:

        if amount > 0:

            if style == 'LimitOrder':
                result = _order_global['trader'].buy(security, amount, price)
            else:
                result = _order_global['trader'].market_buy(security, amount, price)

        elif amount < 0:
            amount = revision_closeable_amount(security, amount)

            if amount != 0:

                if style == 'LimitOrder':
                    result = _order_global['trader'].sell(security, abs(amount), price)
                else:
                    result = _order_global['trader'].market_sell(security, abs(amount), price)
            else:
                print('风控函数 标的: {} 委托方向: Sell 委托类型: {} 回报信息: {}'.format(security, style, '预期卖出数量等于 0 忽略本次下单'))

        if amount != 0:

            if 'message' in result:
                print('委托函数 委托失败 标的: {} 委托方向: {} 委托类型: {} 数量: {} 回报信息: {}'.format(security, 'Buy' if amount > 0 else 'Sell', style, amount, result['message']))
            else:
                print('委托函数 委托成功 标的: {} 委托方向: {} 委托类型: {} 数量: {} 委托编号: {}'.format(security, 'Buy' if amount > 0 else 'Sell', style, amount, result['entrust_id']))
            

        # 下一个tick更新账户信息
        handle_after_order()
    
def parse_positions(data):
    result = {}
    positions = data

    for key in positions:
        
        if key != 'undefined':
            result[key] = parse(positions[key])
    return result

## 格式化返回的数据
def parse(data):
    result = json.loads(json.dumps(data), object_hook=lambda d: X(**d))
    return result

def parse_result(data):
    
    ## 如果存在message
    if ('message' in data):
        print(data['message'])
        return data['message']
    else:
        return parse(data)

## 实盘的限价单函数
def LimitOrderStyle(price):
    return price

# 根据可用资金调整买入股数
def revision_amount(stock, value, amount, price):

    # 如果买入股数 * 价格 * 手续费 大于可用余额 则调整买入股数
    if amount * price > value:
        print('风控函数 标的: {} 预期买入股数: {} 价格: {} 买入价值: {} '.format(stock, amount, price, amount * price))
        # print('风控函数 标的: {} 预期买入股数: {} 价格: {} 可用资金: {}'.format(stock, amount, price, value))
        amount = value / price
        amount = round_amount(amount)
        print('风控函数 大于可用余额: {} 调整买入股数为: {} '.format(value, amount))
        
    return amount

# 根据可卖数量调整卖出股数
def revision_closeable_amount(stock, amount):

    if _order_global['trader'].parse_stock_code(stock) in _order_global['context'].portfolio.positions:
        info = _order_global['context'].portfolio.positions[_order_global['trader'].parse_stock_code(stock)]

        # 获取可卖数量
        closeable_amount = int(info.closeable_amount)

        # 如果绝对值卖出数量大于可卖数量
        if abs(amount) > closeable_amount:
            print('风控函数 标的: {} 预期卖出股数: {}'.format(stock, abs(amount)))
            print('风控函数 标的: {} 持仓可用股数: {}'.format(stock, closeable_amount))
            print('风控函数 标的: {} 预期卖出股数大于持仓可用股数 卖出股数调整为持仓可用股数'.format(stock))
            return 0 - closeable_amount
        else:
            return amount
    else:
        return 0

# 整除股数
def round_amount(amount):
    return int((amount) / 100) * 100