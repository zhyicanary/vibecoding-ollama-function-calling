import re
from typing import Any, Dict, Literal, Optional, TypedDict


class RouteDecision(TypedDict, total=False):
    route: Literal["tool", "chat"]
    tool_name: str
    tool_args: Dict[str, Any]


def _extract_time_args(message: str) -> Dict[str, Any]:
    lowered = message.lower()
    if any(keyword in lowered for keyword in ["日期", "几号", "今天是几号", "今天几号", "当前日期"]):
        return {"timezone": "Asia/Shanghai", "format": "date"}
    if any(keyword in lowered for keyword in ["几点", "几时", "时间", "当前时间"]):
        if any(keyword in lowered for keyword in ["秒", "分"]):
            return {"timezone": "Asia/Shanghai", "format": "full"}
        return {"timezone": "Asia/Shanghai", "format": "time"}
    return {"timezone": "Asia/Shanghai", "format": "full"}


def _extract_city(message: str) -> Optional[str]:
    patterns = [
        r"(?P<city>[\u4e00-\u9fffA-Za-z·\s-]{1,20}?)(?:今天|明天|现在|此刻)?(?:的)?天气",
        r"天气(?:怎么样|如何|情况)?(?:在)?(?P<city>[\u4e00-\u9fffA-Za-z·\s-]{1,20})",
        # 支持“今天<城市>天气如何”的表述
        r"今天(?P<city>[\u4e00-\u9fffA-Za-z·\s-]{1,20})(?:的)?天气",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            city = match.group("city").strip()
            city = re.sub(r"(今天|明天|现在|此刻|的|天气|怎么样|如何|情况)$", "", city).strip()
            if city:
                return city
    return None


def _extract_ticker(message: str) -> Optional[str]:
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", message)
    if match:
        return match.group(0)
    return None


def route_request(message: str) -> RouteDecision:
    normalized = message.strip()
    lowered = normalized.lower()

    # 扩展日期匹配，包含“是多少号”“多少号”等常见提问方式
    if any(keyword in lowered for keyword in ["今天几号", "今天是多少号", "今天多少号", "是多少号", "多少号", "当前日期", "日期", "几号", "几点", "几时", "时间"]):
        return {
            "route": "tool",
            "tool_name": "get_time",
            "tool_args": _extract_time_args(normalized),
        }

    if any(keyword in lowered for keyword in ["天气", "气温", "温度", "下雨", "晴", "阴", "风"]):
        city = _extract_city(normalized)
        if city:
            return {
                "route": "tool",
                "tool_name": "get_weather",
                "tool_args": {"city": city},
            }

    if any(keyword in lowered for keyword in ["股票", "股价", "行情", "涨跌", "a股"]):
        ticker = _extract_ticker(normalized)
        if ticker:
            return {
                "route": "tool",
                "tool_name": "get_stock_price",
                "tool_args": {"ticker": ticker},
            }

    if any(keyword in lowered for keyword in ["课程", "教学大纲", "考核", "智能应用系统设计"]):
        return {
            "route": "tool",
            "tool_name": "query_course_info",
            "tool_args": {"question": normalized},
        }

    return {"route": "chat"}