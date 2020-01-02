#导入smtplib模块
from smtplib import SMTP
from email.mime.text import MIMEText
from email.header import Header

# 封装的邮件对象
class Mail:
    email_client = None
    smtp_host = 'smtp.qq.com'
    from_addr = None
    to_addrs = None
    password = None

    def __init__(self, from_addr, password, to_addrs):
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.password = password

    def send_email(self, subject, content):
        self.email_client = SMTP(self.smtp_host)
        self.email_client.login(self.from_addr, self.password)
        msg = MIMEText(content,'plain','utf-8')
        msg['Subject'] = Header(subject, 'utf-8')#subject
        self.email_client.sendmail(self.from_addr, self.to_addrs, msg.as_string())
