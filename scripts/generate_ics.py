from datetime import datetime, timedelta
import calendar

# 生成指定年份的 IF/IH 交割日
def get_settlement_dates(years):
    events = []
    for year in years:
        for month in [3, 6, 9, 12]:
            # 找第三个星期五
            c = calendar.monthcalendar(year, month)
            if c[0][calendar.FRIDAY] != 0:
                day = c[2][calendar.FRIDAY]
            else:
                day = c[3][calendar.FRIDAY]
            dt = datetime(year, month, day)
            events.append(dt)
    return events

# 生成 ICS 内容
def generate_ics(events):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "PRODID:-//IF/IH 股指期货交割日//CN"
    ]
    for e in events:
        dt = e.strftime("%Y%m%d")
        lines += [
            "BEGIN:VEVENT",
            f"UID:ifih-{dt}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            "SUMMARY:IF/IH 股指期货交割日",
            f"DTSTART;VALUE=DATE:{dt}",
            f"DTEND;VALUE=DATE:{(e + timedelta(days=1)).strftime('%Y%m%d')}",
            "END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines)

# 输出文件
years = [2026, 2027, 2028]  # 可扩展
events = get_settlement_dates(years)
with open("IF_IH.ics", "w", encoding="utf-8") as f:
    f.write(generate_ics(events))
print("ICS 文件已生成")
