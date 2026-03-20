import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar
import re

# ===== 抓取 SSE 官方休市安排公告列表 =====
BASE_URL = "https://www.sse.com.cn"
LIST_URL = "https://www.sse.com.cn/disclosure/dealinstruc/closed/"

def fetch_announcement_urls():
    resp = requests.get(LIST_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for a in soup.select("a[href*='/disclosure/dealinstruc/closed/']"):
        href = a.get("href", "")
        if href.endswith(".shtml"):
            full = BASE_URL + href
            if full not in urls:
                urls.append(full)
    return urls

# ===== 解析公告休市区间 =====
def parse_holiday_ranges(url):
    holidays = []
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n")
    patterns = re.findall(r"(\d{1,2}月\d{1,2}日).{0,15}至.{0,15}(\d{1,2}月\d{1,2}日)", text)
    year = datetime.now().year
    for a, b in patterns:
        try:
            start = datetime.strptime(f"{year}{a}", "%Y%m%d")
            end   = datetime.strptime(f"{year}{b}", "%Y%m%d")
            holidays.append((start.date(), end.date()))
        except:
            continue
    return holidays

# ===== 合并所有解析结果 =====
def get_holiday_ranges():
    urls = fetch_announcement_urls()
    all_ranges = []
    for url in urls:
        rs = parse_holiday_ranges(url)
        for r in rs:
            if r not in all_ranges:
                all_ranges.append(r)
    return all_ranges

# ===== 判断是否交易日（排除周末和休市区间） =====
def is_trading_day(date, holidays):
    if date.weekday() >= 5:
        return False
    for start, end in holidays:
        if start <= date <= end:
            return False
    return True

# ===== 获取交割日并顺延到下一个交易日 =====
def get_settlement_date(year, month, holidays):
    c = calendar.monthcalendar(year, month)
    if c[0][calendar.FRIDAY] != 0:
        day = c[2][calendar.FRIDAY]
    else:
        day = c[3][calendar.FRIDAY]
    dt = datetime(year, month, day)
    while not is_trading_day(dt.date(), holidays):
        dt += timedelta(days=1)
    return dt

def format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_ics(years):
    holidays = get_holiday_ranges()
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "PRODID:-//股指交易关键时间系统//CN",
        "METHOD:PUBLISH"
    ]

    for year in years:
        for month in range(1, 13):
            settle = get_settlement_date(year, month, holidays)
            date_str = settle.strftime("%Y%m%d")
            prev = settle - timedelta(days=1)

            risk_start = prev.replace(hour=0, minute=0, second=0)
            risk_end   = settle.replace(hour=0, minute=0, second=0)
            close_start= settle.replace(hour=14, minute=30, second=0)
            close_end  = settle.replace(hour=15, minute=0, second=0)

            # 交割前一日（风险）
            lines += [
                "BEGIN:VEVENT",
                f"UID:risk-{date_str}",
                f"DTSTAMP:{now}",
                "SUMMARY:交割前一日（高波动）",
                "DESCRIPTION:多空博弈升温，注意减仓/控制风险",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                f"DTSTART:{format_dt(risk_start)}",
                f"DTEND:{format_dt(risk_end)}",
                "END:VEVENT"
            ]

            # 交割日（全天）
            lines += [
                "BEGIN:VEVENT",
                f"UID:settle-{date_str}",
                f"DTSTAMP:{now}",
                "SUMMARY:股指交割日（IF/IH/IC/IM + 期权）",
                "DESCRIPTION:期货与期权同时结算",
                "STATUS:CONFIRMED",
                "TRANSP:TRANSPARENT",
                f"DTSTART;VALUE=DATE:{date_str}",
                f"DTEND;VALUE=DATE:{(settle + timedelta(days=1)).strftime('%Y%m%d')}",
                "END:VEVENT"
            ]

            # 尾盘结算窗口
            lines += [
                "BEGIN:VEVENT",
                f"UID:close-{date_str}",
                f"DTSTAMP:{now}",
                "SUMMARY:尾盘结算窗口（关键）",
                "DESCRIPTION:14:30-15:00 结算博弈趋势波动",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                f"DTSTART:{format_dt(close_start)}",
                f"DTEND:{format_dt(close_end)}",
                "END:VEVENT"
            ]

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

if __name__ == "__main__":
    years = list(range(2026, 2036))
    content = generate_ics(years)
    with open("IF_IH.ics", "w", encoding="utf-8") as f:
        f.write(content)
    print("自动避开休市安排的 ICS 文件已生成")
