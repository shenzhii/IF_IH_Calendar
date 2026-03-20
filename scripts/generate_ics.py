import json
from datetime import datetime, timedelta
import calendar

# ===== 读取休市和调休数据 =====
with open("holidays.json", "r", encoding="utf-8") as f:
    data = json.load(f)

HOLIDAYS = [(datetime.strptime(s, "%Y-%m-%d").date(), datetime.strptime(e, "%Y-%m-%d").date())
            for s, e in data.get("holidays", [])]
WORKDAYS = [datetime.strptime(d, "%Y-%m-%d").date() for d in data.get("workdays", [])]

# ===== 判断是否交易日 =====
def is_trading_day(date):
    if date in WORKDAYS:
        return True
    if date.weekday() >= 5:
        return False
    for start, end in HOLIDAYS:
        if start <= date <= end:
            return False
    return True

# ===== 获取交割日，顺延到下一个交易日 =====
def get_settlement_date(year, month):
    c = calendar.monthcalendar(year, month)
    if c[0][calendar.FRIDAY] != 0:
        day = c[2][calendar.FRIDAY]
    else:
        day = c[3][calendar.FRIDAY]
    dt = datetime(year, month, day)
    while not is_trading_day(dt.date()):
        dt += timedelta(days=1)
    return dt

# ===== 日期格式化 =====
def format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")

# ===== 生成 ICS =====
def generate_ics(years):
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
            settle = get_settlement_date(year, month)
            date_str = settle.strftime("%Y%m%d")
            prev = settle - timedelta(days=1)

            # ===== 交割前一日（高波动风险）=====
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

            # ===== 交割日（全天）=====
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

            # ===== 尾盘结算窗口 =====
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

# ===== 主程序 =====
if __name__ == "__main__":
    years = list(range(2026, 2036))
    content = generate_ics(years)
    with open("IF_IH.ics", "w", encoding="utf-8") as f:
        f.write(content)
    print("完全避开休市和调休的 ICS 文件已生成")
