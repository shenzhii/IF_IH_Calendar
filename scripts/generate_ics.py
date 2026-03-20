import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar
import re

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

def parse_holiday_ranges(url):
    holidays = []
    workdays = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n").replace("（", "(").replace("）", ")").replace(" ", " ")
        
        year = datetime.now().year
        # 匹配休市区间
        patterns = re.findall(r"(\d{1,2})月(\d{1,2})日.*?至.*?(\d{1,2})月(\d{1,2})日", text)
        for m1, d1, m2, d2 in patterns:
            try:
                start = datetime(year, int(m1), int(d1)).date()
                end   = datetime(year, int(m2), int(d2)).date()
                holidays.append((start, end))
            except:
                continue
        # 匹配调休工作日
        work_patterns = re.findall(r"(\d{1,2})月(\d{1,2})日.*?补(上班|工作)", text)
        for m, d, _ in work_patterns:
            try:
                wd = datetime(year, int(m), int(d)).date()
                workdays.append(wd)
            except:
                continue
    except:
        pass
    return holidays, workdays

def get_holiday_and_workdays():
    urls = fetch_announcement_urls()
    all_holidays = []
    all_workdays = []
    for url in urls:
        h, w = parse_holiday_ranges(url)
        for r in h:
            if r not in all_holidays:
                all_holidays.append(r)
        for d in w:
            if d not in all_workdays:
                all_workdays.append(d)
    return all_holidays, all_workdays

def is_trading_day(date, holidays, workdays):
    if date in workdays:
        return True
    if date.weekday() >= 5:
        return False
    for start, end in holidays:
        if start <= date <= end:
            return False
    return True

def get_settlement_date(year, month, holidays, workdays):
    c = calendar.monthcalendar(year, month)
    if c[0][calendar.FRIDAY] != 0:
        day = c[2][calendar.FRIDAY]
    else:
        day = c[3][calendar.FRIDAY]
    dt = datetime(year, month, day)
    while not is_trading_day(dt.date(), holidays, workdays):
        dt += timedelta(days=1)
    return dt

def format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_ics(years):
    holidays, workdays = get_holiday_and_workdays()
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
            settle = get_settlement_date(year, month, holidays, workdays)
            date_str = settle.strftime("%Y%m%d")
            prev = settle - timedelta(days=1)

            # 风险日
            lines += [
                "BEGIN:VEVENT",
                f"UID:risk-{date_str}",
                f"DTSTAMP:{now}",
                "SUMMARY:交割前一日（高波动）",
                "DESCRIPTION:多空博弈升温，注意减仓/控制风险",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                f"DTSTART:{format_dt(prev.replace(hour=0, minute=0, second=0))}",
                f"DTEND:{format_dt(settle.replace(hour=0, minute=0, second=0))}",
                "END:VEVENT"
            ]

            # 交割日
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

            # 尾盘窗口
            lines += [
                "BEGIN:VEVENT",
                f"UID:close-{date_str}",
                f"DTSTAMP:{now}",
                "SUMMARY:尾盘结算窗口（关键）",
                "DESCRIPTION:14:30-15:00 结算博弈趋势波动",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                f"DTSTART:{format_dt(settle.replace(hour=14, minute=30, second=0))}",
                f"DTEND:{format_dt(settle.replace(hour=15, minute=0, second=0))}",
                "END:VEVENT"
            ]

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

if __name__ == "__main__":
    years = list(range(2026, 2036))
    content = generate_ics(years)
    with open("IF_IH.ics", "w", encoding="utf-8") as f:
        f.write(content)
    print("完全避开休市和调休的 ICS 文件已生成")
