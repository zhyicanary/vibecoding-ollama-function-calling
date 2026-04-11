import requests
import json
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
from email.header import Header


def send_email(to_email, subject, content, from_email=None, from_password=None, smtp_server='smtp.qq.com', smtp_port=465):
    """
    通过SMTP协议发送邮件
    :param to_email: 收件人邮箱
    :param subject: 邮件主题
    :param content: 邮件内容
    :param from_email: 发件人邮箱 (默认为环境变量SMTP_FROM_EMAIL或占位符)
    :param from_password: 发件人密码/授权码 (默认为环境变量SMTP_PASSWORD或占位符)
    :param smtp_server: SMTP服务器地址 (默认 smtp.qq.com)
    :param smtp_port: SMTP端口 (默认 465)
    :return: JSON格式的发送结果，包含status(状态)、message(信息)、to(收件人)、subject(主题)、send_time(发送时间)
    """
    import os
    
    if from_email is None:
        from_email = os.environ.get('FROM_EMAIL', 'your_email@example.com')
    if from_password is None:
        from_password = os.environ.get('SMTP_PASSWORD', 'your_password')
    
    send_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
    
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = from_email
        msg['To'] = to_email
        
        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(from_email, from_password)
                server.sendmail(from_email, [to_email], msg.as_string())
        except Exception as ssl_err:
            if 'SSL' in str(ssl_err) or 'SSLError' in str(ssl_err):
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(from_email, from_password)
                    server.sendmail(from_email, [to_email], msg.as_string())
            else:
                raise
        
        result = {
            "status": "success",
            "message": "邮件发送成功",
            "to": to_email,
            "subject": subject,
            "send_time": send_time
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        result = {
            "status": "error",
            "message": f"邮件发送失败: {str(e)}",
            "to": to_email,
            "subject": subject,
            "send_time": send_time
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_current_time(timezone='Asia/Shanghai', format='full'):
    """获取当前时间"""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        if format == 'date':
            return now.strftime('%Y年%m月%d日')
        elif format == 'time':
            return now.strftime('%H:%M:%S')
        else:
            return now.strftime('%Y年%m月%d日 %H:%M:%S %Z')
    except Exception as e:
        return f"获取时间失败: {str(e)}"


def get_weather(city):
    """获取城市天气"""
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('current_condition', [{}])[0]
            
            weather_desc = current.get('weatherDesc', [{}])[0].get('value', '未知')
            temp_C = current.get('temp_C', 'N/A')
            humidity = current.get('humidity', 'N/A')
            wind_kmh = current.get('windspeedKmh', 'N/A')
            feelslike = current.get('FeelsLikeC', 'N/A')
            
            return f"{city}天气:\n- 温度: {temp_C}°C (体感 {feelslike}°C)\n- 天气: {weather_desc}\n- 湿度: {humidity}%\n- 风速: {wind_kmh} km/h"
        else:
            return f"无法获取{city}的天气信息"
    except Exception as e:
        return f"获取天气失败: {str(e)}"


def get_stock_price_cn(ticker):
    """
    获取A股股票价格信息
    :param ticker: 6位股票代码，如 600519
    :return: JSON格式的股价信息
    """
    try:
        if ticker.startswith("6"):
            code = f"sh{ticker}"
        else:
            code = f"sz{ticker}"

        url = f"https://hq.sinajs.cn/list={code}"
        headers = {"Referer": "https://finance.sina.com/"}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()

        data = res.text.split('"')[1].split(',')

        if len(data) < 3:
            return json.dumps({
                "status": "error",
                "message": f"未找到股票：{ticker}"
            }, ensure_ascii=False)

        result = {
            "name": data[0],
            "ticker": ticker,
            "current_price": float(data[3]),
            "open": float(data[1]),
            "last_close": float(data[2]),
            "high": float(data[4]),
            "low": float(data[5]),
            "change_percent": round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 2),
            "status": "success"
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取失败：{str(e)}"
        }, ensure_ascii=False)
        