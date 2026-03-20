import json
from datetime import datetime, timedelta
import calendar

# ===== 读取手动维护的休市与调休文件 =====
with open("holidays.json", "r", encoding="utf-8") as f:
    data = json.load(f)

holidays = [(datetime.strptime(s, "%Y-%m-%d").date(), datetime.strptime(e, "%Y-%m-%d").date()) 
            for s, e in data["holidays"]]
workdays = [datetime.strptime(d, "%Y-%m-%d").date() for d in data["workdays"]]

def is_trading_day(date):
    if date in workdays:
        return True
    if date.weekday() >= 5:  # 周末
        return False
    for start, end in holidays:
        if start <= date <= end:
            return False
    return True

def get_settlement_date(year, month):
    # 第三周五
    c = calendar.monthcalendar(year, month)
    if c[0][calendar.FRIDAY] != 0:
        day = c[2][calendar.FRIDAY]
    else:
        day = c[3][calendar.FRIDAY]
    dt = datetime(year, month, day)
    # 顺延到下一个交易日
    while not is_trading_day(dt.date()):
        dt += timedelta(days=1)
    return dt

def format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_ics(year):
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "PRODID:-//股指交易关键时间系统//CN",
        "METHOD:PUBLISH"
    ]

    for month in range(1, 13):
        settle = get_settlement_date(year, month)
        prev = settle - timedelta(days=1)
        date_str = settle.strftime("%Y%m%d")

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

        # 尾盘结算窗口
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
    content = generate_ics(2026)
    with open("IF_IH_2026.ics", "w", encoding="utf-8") as f:
        f.write(content)
    print("2026 年交割日 ICS 已生成，已顺延至交易日")
