import re
import json
from trade_order.src.zt_clienttrader import ZTClientTrader
from trade_order.src.mail import Mail

# 通用对象转化
class X(object):

    def __init__(self, **kwargs):
        
        for name, value in kwargs.items():
            setattr(self, name, value)

class ZhongTaiTrader:

    # 中泰接口基础参数
    mail = None

    def __init__(self):
        self.trader = ZTClientTrader()

    def send_email(self, title, context):

        if self.mail != None:
            self.mail.send_email(title, context)
        else:
            print('### 未开启邮件通知 ###')

    # 启动客户端
    def run_client(self, client_path):
        self.trader.connect(client_path)

    # 启动下单邮件推送
    # account 发送者
    # password 发送者密码
    # 接收者
    def run_email(self, account, password, form_account):

        if account != None and password != None and form_account != None:
            self.mail = Mail(account, password, form_account)
            print('### 已开启邮件通知 ###')
        else:
            print('### 未开启邮件通知 ###')

    # 登录
    def login(self, account, password):
        self.trader.login(account, password)
        self.send_email('中泰账号 ' + account + ' 登录成功', '')

    # 限价买入
    def buy(self, security, amount, price):
        result = self.trader.buy(security, price, amount)

        if 'message' in result:
            self.send_email('中泰账号限价单买入失败', '错误原因' + result['message'])
        else:
            self.send_email('中泰账号限价单买入成功' + security, '买入股数' + str(amount) + ', 价格' + str(price))

        print(result)
        return result

    # 限价卖出
    def sell(self, security, amount, price):
        result = self.trader.sell(security, price, amount)

        if 'message' in result:
            self.send_email('中泰账号限价单卖出失败', '错误原因' + result['message'])
        else:
            self.send_email('中泰账号限价单卖出成功' + security, '卖出股数' + str(amount) + ', 价格' + str(price))

        print(result)
        return result

    # 市价买入
    def market_buy(self, security, amount):
        result = self.trader.market_buy(security, amount)

        if 'message' in result:
            self.send_email('中泰账号市价单买入失败', '错误原因' + result['message'])
        else:
            self.send_email('中泰账号市价单买入成功' + security, '买入股数' + str(amount))
        
        print(result)
        return result

    # 市价卖出
    def market_sell(self, security, amount):
        result = self.trader.market_sell(security, amount)

        if 'message' in result:
            self.send_email('中泰账号市价单卖出失败', '错误原因' + result['message'])
        else:
            self.send_email('中泰账号市价单卖出成功' + security, '卖出股数' + str(amount))
        
        print(result)
        return result

    # 撤单    
    def cancel_entrust(self, entrust_id):
        result = self.trader.cancel_entrust(entrust_id)
        print(result)
        self.send_email('中泰账号撤单', '撤单结果: ' + json.dumps(result))

    # 持仓
    def position(self):
        result = self.trader.get_position()
        data = result['cash'] 
        positions_data = result['position']
        portfolio_return = 0
        positions = {}

        for item in positions_data:
            security = self.parse_stock_code(item.get('证券代码'))
            positions[security] = {
                'security_name': item.get('证券名称'),
                'security': security,
                'price': item.get('市价'),
                'acc_avg_cost': item.get('参考成本'),
                'avg_cost': item.get('参考成本'),
                'locked_amount': int(item.get('持股数量')) - int(item.get('可用余额')), 
                'value': float(item.get('参考市值')),
                'closeable_amount': float(item.get('可用余额')),
                'total_amount': int(item.get('持股数量')),
                'returns': float(item.get('累计盈亏2')),
                'current_value': float(item.get('参考盈亏')),
                'current_returns': float(item.get('盈亏比例(%)'))
            }

            portfolio_return = portfolio_return + float(item.get('参考盈亏'))

        portfolio = {
            'total_value': float(data.get('总资产')),
            'available_cash': float(data.get('可用金额')),
            'transferable_cash': float(data.get('可取金额')),
            'positions_value': float(data.get('股票市值')),
            'returns': portfolio_return
        }

        result = {
            'positions': positions,
            'portfolio': portfolio
        }

        print(result)
        return result

    # 交易列表
    def trades(self):
        result = self.trader.today_trades()
        _list = []
        data = self.parse_result_list(result)

        if 'data' in data:

            for item in data['data']:
                _list.append(self.parse({
                    'trade_id': item.get('合同编号'),
                    'security': self.parse_stock_code(item.get('证券代码'))
                }))
            
            return _list
        else:
            return data

    # 委托列表
    def today_entrusts(self):
        result = self.trader.today_entrusts()
        _list = []
        data = self.parse_result_list(result)
        
        if 'data' in data:

            for item in data['data']:
                _list.append(self.parse({
                    'order_id': item.get('合同编号'),
                    'security': self.parse_stock_code(item.get('证券代码')),
                    'status': item.get('委托状态')
                }))
            return _list
        else:
            return data

    # 撤单列表
    def cancel_entrusts(self):
        result = self.trader.cancel_entrusts()
        _list = []
        data = self.parse_result_list(result)
        
        if 'data' in data:

            for item in data['data']:
                _list.append(self.parse({
                    'order_id': item.get('合同编号'),
                    'security': self.parse_stock_code(item.get('证券代码')),
                    'status': item.get('委托状态')
                }))
            
            return _list
        else:
            return data

    def auto_ipo(self):
        self.trader.auto_ipo()

    def parse_result_order(self, result):

        if result['Status'] == 0:
            return {
                'entrust_id': result['Data'][0]['Wtbh']
            }
        else:
            return {
                'message': result['Message']
            }

    def parse_result_list(self, result):

        # 如果是数组 说明数据正确返回
        if isinstance (result, list):
            return {
                'data': result
            }
        else:
            return {
                'message': result
            }

    # 处理股票代码为聚宽格式的
    def parse_stock_code(self, code):

        # 将正则表达式编译成Pattern对象
        regXSHE = re.compile('^(002|000|300|1599|1610)')
        regXSHG = re.compile('^(600|601|603|51)')

        matchXSHE = regXSHE.match(code)
        matchXSHG = regXSHG.match(code)

        if matchXSHE and len(matchXSHE.group()):
            return '.'.join([code, 'XSHE'])
        elif matchXSHG and len(matchXSHG.group()):
            return '.'.join([code, 'XSHG'])

    ## 格式化返回的数据
    def parse(self, data):
        result = json.loads(json.dumps(data), object_hook=lambda d: X(**d))
        return result