# 简单的tick级别实时交易 支持聚宽语法 
# 依赖 以下类库

# jqdatasdk 聚宽提供的历史行情
# trade_bundle 开源的python实时tick行情 以及策略运行框架 [后续会提供历史tick数据的接口调用]
# trade_order 开源的python实盘交易接口
from jqdatasdk import *
from trade_bundle.live_trade import *
from trade_order.order_api import *

def initialize(context):
    print('##### initialize #####')

    # 订阅多个标的
    subscribe('600519.XSHG', 'tick')
    subscribe('000858.XSHE', 'tick')

    # 测试jqdata数据
    print(get_price('000001.XSHE', start_date='2015-12-01 14:00:00', end_date='2015-12-02 12:00:00', frequency='1m'))

def before_trading_start(context):
    print('##### before_trading_start #####')

def handle_tick(context, tick):
    print('##### handle_tick #####')
    print(tick.current)
    # order('600519.XSHG', 100)

def after_trading_end(context):
    print('##### after_trading_end #####')
    unsubscribe_all()

# 初始化jqdatasdk
auth('聚宽账号','聚宽密码')

# 初始化实盘模块
init_trader(g, context, '资金账号', '资金密码', r'E:\中泰证券独立下单\xiadan.exe')

# 初始化实时tick行情
init_current_bundle(initialize, before_trading_start, after_trading_end, handle_tick)
