"""ฟีเจอร์เสริม: ตั้งเวลาการนอน + ไฟล์ปฏิทินแจ้งเตือน (.ics)

แยกไว้ไฟล์เดียว ถ้าไม่อยากใช้ ให้ตั้ง FEATURE_SCHEDULE = False ใน app.py (หรือลบไฟล์นี้ + ส่วนที่ติดป้าย [schedule])
"""
from datetime import date, datetime, time, timedelta, timezone
from statistics import median
from uuid import uuid4

TZ = "Asia/Bangkok"
DEFAULT = {"weekday_wake": time(7, 0), "weekend_wake": time(8, 30), "target_hours": 8.0, "remind_before": 30}
DAYS_ICS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DAYS_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"]


def wake_for(d: date, s: dict) -> time:
    """เวลาตื่นของเช้าวันที่ d (จ–ศ ใช้เวลาวันธรรมดา, ส–อา ใช้เวลาวันหยุด)"""
    return s["weekday_wake"] if d.weekday() < 5 else s["weekend_wake"]


def latency_estimate(entries: list[dict]) -> int:
    """ปกติใช้เวลากี่นาทีกว่าจะหลับ — ใช้ข้อมูลของผู้ใช้เอง ถ้ายังไม่มีใช้ 15 นาที"""
    vals = [e["sleep_latency_minutes"] for e in entries if e.get("sleep_latency_minutes") is not None]
    return int(median(vals)) if vals else 15


def planned_bed(d: date, s: dict, latency: int) -> datetime:
    """เวลาที่ควรขึ้นเตียง สำหรับคืนที่ตื่นเช้าวันที่ d"""
    wake = datetime.combine(d, wake_for(d, s))
    return wake - timedelta(hours=float(s["target_hours"]), minutes=latency)


def actual_bed(e: dict) -> datetime:
    """เวลาเข้านอนจริงเป็น datetime (เข้านอนหลังเที่ยงคืน = วันเดียวกับวันที่ตื่น)"""
    d = e["date"]
    day = d if e["bed"] < e["wake"] else d - timedelta(days=1)
    return datetime.combine(day, e["bed"])


def tonight(now: datetime, s: dict, latency: int) -> dict:
    """คืนที่กำลังจะถึง: ตื่นเมื่อไร ควรเข้านอนเมื่อไร เหลืออีกกี่นาที"""
    now = now.replace(tzinfo=None)
    for add in (0, 1):
        d = now.date() + timedelta(days=add)
        wake = datetime.combine(d, wake_for(d, s))
        if wake > now:
            bed = planned_bed(d, s, latency)
            return {"wake": wake, "bed": bed, "minutes_left": (bed - now).total_seconds() / 60,
                    "sleep_if_now": (wake - now).total_seconds() / 3600 - latency / 60}
    raise RuntimeError("unreachable")


def adherence(entries: list[dict], s: dict, latency: int, tolerance: int = 30) -> dict:
    """ทำตามเวลาที่ตั้งได้กี่คืน (เข้านอนช้ากว่าแผนไม่เกิน tolerance นาที = ตรงเวลา)"""
    delays = [(actual_bed(e) - planned_bed(e["date"], s, latency)).total_seconds() / 60 for e in entries]
    if not delays:
        return {"nights": 0, "on_time": 0, "avg_delay": 0.0, "delays": []}
    return {"nights": len(delays), "on_time": sum(x <= tolerance for x in delays),
            "avg_delay": sum(delays) / len(delays), "delays": delays}


def fmt_minutes(m: float) -> str:
    m = int(round(abs(m)))
    h, mm = divmod(m, 60)
    return f"{h} ชม. {mm} นาที" if h else f"{mm} นาที"


# ---------------------------------------------------------------- ปฏิทิน .ics
def _vevent(start: datetime, byday: list[str], remind: int, title: str, desc: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "\r\n".join([
        "BEGIN:VEVENT", f"UID:{uuid4()}@nonpormai", f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={TZ}:{start:%Y%m%dT%H%M%S}",
        f"DTEND;TZID={TZ}:{start + timedelta(minutes=15):%Y%m%dT%H%M%S}",
        f"RRULE:FREQ=WEEKLY;BYDAY={','.join(byday)}",
        f"SUMMARY:{title}", f"DESCRIPTION:{desc}", "TRANSP:TRANSPARENT",
        "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{title}", f"TRIGGER:-PT{remind}M", "END:VALARM",
        "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{title}", "TRIGGER:PT0M", "END:VALARM",
        "END:VEVENT"])


def build_ics(s: dict, latency: int, today: date) -> str:
    """นัด "ได้เวลาเข้านอน" ซ้ำทุกสัปดาห์ แยกคืนก่อนวันทำงาน / คืนก่อนวันหยุด พร้อมเตือนล่วงหน้า"""
    groups: dict[time, list[int]] = {}
    for wake_wd in range(7):                       # วันที่ตื่น จ(0)..อา(6)
        d = today + timedelta(days=(wake_wd - today.weekday()) % 7 + 7)   # วันตัวอย่างในอนาคต
        bed = planned_bed(d, s, latency)
        groups.setdefault(bed.time(), []).append(bed.weekday())
    events = []
    for t, weekdays in groups.items():
        first = min(today + timedelta(days=(wd - today.weekday()) % 7) for wd in weekdays)
        start = datetime.combine(first, t)
        desc = (f"เป้า {s['target_hours']:g} ชม. · เผื่อเวลากว่าจะหลับ {latency} นาที — จากแอป นอนพอมั้ย")
        events.append(_vevent(start, [DAYS_ICS[w] for w in sorted(weekdays)], int(s["remind_before"]),
                              "🌙 ได้เวลาเข้านอนแล้ว", desc))
    tz = "\r\n".join(["BEGIN:VTIMEZONE", f"TZID:{TZ}", "BEGIN:STANDARD", "DTSTART:19700101T000000",
                      "TZOFFSETFROM:+0700", "TZOFFSETTO:+0700", "TZNAME:ICT", "END:STANDARD", "END:VTIMEZONE"])
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//nonpormai//sleep schedule//TH",
                        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:นอนพอมั้ย", tz, *events,
                        "END:VCALENDAR"]) + "\r\n"
