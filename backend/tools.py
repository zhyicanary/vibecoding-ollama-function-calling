import requests
import json
import time
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os
from urllib.parse import quote

rag_vectorstore = None
rag_retriever = None
rag_reranker = None
rag_llm = None
rag_prompt = None
rag_initialized = False


def init_rag():
    """初始化 RAG 系统"""
    global rag_vectorstore, rag_retriever, rag_reranker, rag_llm, rag_prompt, rag_initialized
    
    if rag_initialized:
        print("[RAG] 已初始化，跳过")
        return {"status": "success", "message": "RAG 系统已初始化"}
    
    print("[RAG] 开始初始化...")
    start_time = time.time()
    
    from langchain_community.document_loaders import UnstructuredMarkdownLoader
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    from langchain_ollama import OllamaEmbeddings, ChatOllama
    from langchain_community.vectorstores import Chroma
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnableLambda
    from langchain_community.retrievers import BM25Retriever
    from langchain_classic.retrievers import EnsembleRetriever
    from sentence_transformers import CrossEncoder
    
    md_path = os.path.join(os.path.dirname(__file__), os.environ.get('COURSE_DOC_PATH', '../《智能应用系统设计》课程介绍.md'))
    
    if not os.path.exists(md_path):
        return {"status": "error", "message": f"课程介绍文件不存在: {md_path}"}
    
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()
    
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False
    )
    header_splits = header_splitter.split_text(md_text)
    
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "，", " ", ""]
    )
    splits = char_splitter.split_documents(header_splits)
    
    embeddings = OllamaEmbeddings(
        model="qwen3-embedding:4b",
        base_url="http://localhost:11434"
    )
    
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    bm25_retriever = BM25Retriever.from_documents(splits)
    bm25_retriever.k = 6
    
    rag_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5]
    )
    
    rag_reranker = CrossEncoder("BAAI/bge-reranker-base")
    
    rag_prompt = ChatPromptTemplate.from_template("""
你是一个课程信息助手。请严格根据下方【参考资料】回答用户问题。

规则：
- 只能使用【参考资料】中出现的信息
- 如果资料中没有明确答案，请回答"根据已有资料无法确认"
- 不要编造或推测任何数字、名称

【参考资料】
{context}

【用户问题】
{question}

【回答】
""")
    
    rag_llm = ChatOllama(
        model="qwen3:8b",
        base_url="http://localhost:11434",
        temperature=0
    )
    
    rag_vectorstore = vectorstore
    rag_initialized = True
    
    elapsed = time.time() - start_time
    print(f"[RAG] 初始化完成，耗时 {elapsed:.2f}秒")
    
    return {"status": "success", "message": "RAG 系统初始化成功"}


def query_course(question):
    """查询课程信息"""
    global rag_retriever, rag_reranker, rag_llm, rag_prompt, rag_initialized
    
    print(f"[RAG] query_course 调用，rag_initialized={rag_initialized}")
    
    if not rag_initialized:
        init_result = init_rag()
        if init_result.get("status") != "success":
            return json.dumps(init_result, ensure_ascii=False)
    
    try:
        print(f"[RAG] 执行检索: {question[:20]}...")
        docs = rag_retriever.invoke(question)
        
        if not docs:
            return "未找到相关内容，请尝试其他问题"
        
        pairs = [[question, doc.page_content] for doc in docs]
        scores = rag_reranker.predict(pairs)
        scored_docs = list(zip(docs, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_docs = [doc for doc, score in scored_docs[:4]]
        
        context = "\n\n---\n\n".join(
            f"[来源：{doc.metadata}]\n{doc.page_content}"
            for doc in top_docs
        )
        
        from langchain_core.runnables import RunnablePassthrough, RunnableLambda
        from langchain_core.output_parsers import StrOutputParser
        
        def get_context(x):
            return context
        
        chain = (
            {"context": RunnableLambda(get_context), "question": RunnablePassthrough()}
            | rag_prompt
            | rag_llm
            | StrOutputParser()
        )
        
        answer = chain.invoke(question)
        return answer
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"查询失败: {str(e)}"}, ensure_ascii=False)


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
        def weather_code_to_text(code):
            code_map = {
                0: "晴朗",
                1: "大致晴朗",
                2: "局部多云",
                3: "多云",
                45: "有雾",
                48: "有雾凇",
                51: "小毛毛雨",
                53: "毛毛雨",
                55: "强毛毛雨",
                61: "小雨",
                63: "中雨",
                65: "大雨",
                71: "小雪",
                73: "中雪",
                75: "大雪",
                80: "阵雨",
                81: "强阵雨",
                82: "猛烈阵雨",
                95: "雷暴",
                96: "雷暴伴冰雹",
                99: "强雷暴伴冰雹",
            }
            return code_map.get(int(code), "未知")

        city = city.strip()
        city_encoded = quote(city)

        # 先通过 Open-Meteo 地理编码获取经纬度，再查实时天气，避免中文城市名直连不稳定。
        geocode_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={city_encoded}&count=1&language=zh&format=json"
        )
        geocode_response = requests.get(
            geocode_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,*/*",
            },
        )

        if geocode_response.status_code == 200:
            geocode_data = geocode_response.json()
            results = geocode_data.get("results") or []
            if results:
                place = results[0]
                latitude = place["latitude"]
                longitude = place["longitude"]
                location_name = place.get("name", city)

                forecast_url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={latitude}&longitude={longitude}"
                    "&current=temperature_2m,apparent_temperature,weather_code,relative_humidity_2m,wind_speed_10m"
                    "&timezone=auto"
                )
                forecast_response = requests.get(
                    forecast_url,
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json,*/*",
                    },
                )

                if forecast_response.status_code == 200:
                    forecast_data = forecast_response.json()
                    current = forecast_data.get("current", {})
                    weather_code = current.get("weather_code", -1)
                    temp_c = current.get("temperature_2m", "N/A")
                    feels_like = current.get("apparent_temperature", "N/A")
                    humidity = current.get("relative_humidity_2m", "N/A")
                    wind_kmh = current.get("wind_speed_10m", "N/A")
                    weather_desc = weather_code_to_text(weather_code)

                    return (
                        f"{location_name}天气:\n"
                        f"- 温度: {temp_c}°C (体感 {feels_like}°C)\n"
                        f"- 天气: {weather_desc}\n"
                        f"- 湿度: {humidity}%\n"
                        f"- 风速: {wind_kmh} km/h"
                    )

        # 回退到 wttr.in，避免单一服务故障
        wttr_url = f"https://wttr.in/{city_encoded}?format=j1&lang=zh-cn"
        response = requests.get(
            wttr_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
            },
        )

        if response.status_code == 200:
            data = response.json()
            current = data.get('current_condition', [{}])[0]

            weather_desc = current.get('weatherDesc', [{}])[0].get('value', '未知')
            temp_C = current.get('temp_C', 'N/A')
            humidity = current.get('humidity', 'N/A')
            wind_kmh = current.get('windspeedKmh', 'N/A')
            feelslike = current.get('FeelsLikeC', 'N/A')

            return f"{city}天气:\n- 温度: {temp_C}°C (体感 {feelslike}°C)\n- 天气: {weather_desc}\n- 湿度: {humidity}%\n- 风速: {wind_kmh} km/h"

        status = response.status_code if response is not None else 'N/A'
        return f"无法获取{city}的天气信息（HTTP {status}）"
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


def send_dingtalk(message, webhook_url=None):
    """
    发送钉钉消息到群机器人
    :param message: 消息内容
    :param webhook_url: 钉钉机器人webhook地址（从钉钉群设置->群机器人->webhook获取）
    :return: JSON格式的发送结果
    """
    import os
    
    if webhook_url is None:
        webhook_url = os.environ.get('DINGTALK_WEBHOOK_URL', '')
    
    send_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
    
    try:
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"{message}\n发送时间: {send_time}"
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result_data = response.json()
            if result_data.get('errcode') == 0:
                return json.dumps({
                    "status": "success",
                    "message": "钉钉消息发送成功",
                    "content": message,
                    "send_time": send_time
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"发送失败: {result_data.get('errmsg', '未知错误')}",
                    "content": message,
                    "send_time": send_time
                }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"HTTP错误: {response.status_code}",
                "content": message,
                "send_time": send_time
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"发送失败: {str(e)}",
            "content": message,
            "send_time": send_time
        }, ensure_ascii=False, indent=2)
        