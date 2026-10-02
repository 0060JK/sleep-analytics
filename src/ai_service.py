"""ตอบคำถามเรื่องการนอน (เทียบกับ ai_service ในตัวอย่าง)

ตอนนี้ตอบด้วยกฎที่ตั้งไว้ · Step 3 จะส่ง build_context() ไปให้ LLM แทน
หลักเดียวกับตัวอย่าง: ส่ง "สถิติสรุป" ไปให้ AI ไม่ใช่ข้อมูลดิบทุกแถว
"""
from stats_service import cause_counts

QUALITY_TH = {"Good": "ดี", "Fair": "พอใช้", "Poor": "แย่"}


def build_context(period: str, stats: dict, df, target: tuple[float, float]) -> str:
    causes = cause_counts(df).head(3)
    lines = [
        f"ช่วงข้อมูล: {period} ({stats['nights']} คืน) · ช่วงชั่วโมงนอนที่แนะนำ {target[0]:.0f}–{target[1]:.0f} ชม.",
        f"นอนเฉลี่ย {stats['mean']:.1f} ชม. (มัธยฐาน {stats['median']:.1f}, SD {stats['std']:.2f})",
        f"นอนไม่ถึงเกณฑ์ {stats['short_nights']} คืน · หนี้การนอนสะสม {stats['sleep_debt']:.1f} ชม.",
        f"เวลาเข้านอนเฉลี่ย {stats['bed_avg']} (คลาดเคลื่อน ±{stats['bed_std_min']:.0f} นาที)",
        f"แนวโน้ม {stats['slope'] * 60:+.0f} นาที/คืน · คาดการณ์ค่าเฉลี่ยสัปดาห์หน้า {stats['forecast']:.1f} ชม.",
        f"โมเดลประเมินคืนที่คุณภาพแย่ {stats['poor_share']:.0%} · ดี {stats['good_share']:.0%}",
        "ปัจจัยที่พบบ่อย: " + (", ".join(f"{k} ({v} คืน)" for k, v in causes.items()) or "ไม่พบ"),
    ]
    last = df.iloc[-1]
    raw = last["Raw"]
    lines.append(
        f"คืนล่าสุด ({last['Date']:%d/%m}): เข้านอน {last['Bedtime']:%H:%M} ตื่น {last['Wake']:%H:%M} "
        f"นอน {last['Hours']:.1f} ชม. · โมเดลประเมินคุณภาพ {QUALITY_TH[last['Quality']]} "
        f"(โอกาสนอนแย่ {last['P_Poor']:.0%}) · สาเหตุที่น่าจะเป็น: {', '.join(last['Causes']) or 'ไม่พบ'}")
    answers = {"ใช้จอก่อนนอน (นาที)": raw.get("bedtime_screen_time_minutes"),
               "ไถโซเชียลจนนอนช้า": raw.get("doomscroller"), "ระดับเครียด (1-10)": raw.get("stress_score"),
               "เวลาก่อนหลับ (นาที)": raw.get("sleep_latency_minutes"),
               "ตื่นกลางดึก (ครั้ง)": raw.get("number_of_night_wakeups")}
    lines.append("คำตอบของคืนล่าสุด: " + ", ".join(f"{k}={v}" for k, v in answers.items() if v is not None))
    return "\n".join(lines)


def _trend(stats):
    s = stats["slope"] * 60
    if s <= -5:
        t = f"ชั่วโมงนอน **ลดลง** เฉลี่ย {abs(s):.0f} นาทีต่อคืน"
    elif s >= 5:
        t = f"ชั่วโมงนอน **เพิ่มขึ้น** เฉลี่ย {s:.0f} นาทีต่อคืน"
    else:
        t = "ชั่วโมงนอน **ค่อนข้างคงที่**"
    return (f"**แนวโน้ม:** {t} ค่าเฉลี่ยล่าสุด 7 คืน (MA7) อยู่ที่ {stats['ma7']:.1f} ชม. "
            f"ถ้ายังเป็นแบบนี้ สัปดาห์หน้าคาดว่าจะนอนเฉลี่ยราว **{stats['forecast']:.1f} ชม./คืน**")


def _causes(df):
    c = cause_counts(df).head(3)
    if c.empty:
        return "**สาเหตุ:** ยังไม่พบปัจจัยเด่นจากคำตอบที่บันทึกไว้"
    items = "\n".join(f"- {k} — พบใน {v} จาก {len(df)} คืน" for k, v in c.items())
    return "**ปัจจัยที่โมเดลชี้ว่าเป็นสาเหตุบ่อยที่สุด:**\n" + items


def _debt(stats, target):
    return (f"**ความเพียงพอ:** เฉลี่ย {stats['mean']:.1f} ชม./คืน นอนไม่ถึง {target[0]:.0f} ชม. "
            f"{stats['short_nights']} จาก {stats['nights']} คืน หนี้การนอนสะสม **{stats['sleep_debt']:.1f} ชม.**")


def _tips(stats, df):
    tips = []
    top = cause_counts(df).index.tolist()
    if "ไถโซเชียลจนนอนช้า" in top or "ใช้จอก่อนนอนนาน" in top:
        tips.append("วางมือถือนอกห้องนอน หรือตั้งเวลาปิดแอปโซเชียลก่อนนอน 30–60 นาที")
    if stats["bed_std_min"] > 45:
        tips.append(f"เวลาเข้านอนแกว่ง ±{stats['bed_std_min']:.0f} นาที ลองล็อกเวลาเข้านอนให้ใกล้เคียงกันทุกคืน")
    if "ความเครียด" in top:
        tips.append("จดสิ่งที่ค้างในหัวก่อนนอน หรือหายใจช้าๆ 5 นาทีเพื่อลดความเครียด")
    if stats["mean"] < 7:
        tips.append(f"เข้านอนเร็วขึ้นราว {max(7 - stats['mean'], 0.25) * 60:.0f} นาที แทนการตื่นสายขึ้น")
    tips = tips or ["รักษารูปแบบการนอนแบบนี้ไว้ได้เลย"]
    return "**คำแนะนำ:**\n" + "\n".join(f"- {t}" for t in tips)


def ask_sleep_ai(question: str, period: str, stats: dict, df, target: tuple[float, float]) -> str:
    q = question.lower()
    parts = []
    if any(k in q for k in ["แนวโน้ม", "trend", "สัปดาห์หน้า", "คาด"]):
        parts.append(_trend(stats))
    if any(k in q for k in ["สาเหตุ", "เพราะ", "ทำไม", "ปัจจัย", "cause"]):
        parts.append(_causes(df))
    if any(k in q for k in ["พอ", "หนี้", "debt", "ชั่วโมง"]):
        parts.append(_debt(stats, target))
    if any(k in q for k in ["แนะนำ", "ควร", "ทำยังไง", "วิธี", "tip"]):
        parts.append(_tips(stats, df))
    if not parts:   # คำถามทั่วไป → สรุปทั้งหมด
        parts = [_debt(stats, target), _trend(stats), _causes(df), _tips(stats, df)]
    return "\n\n".join(parts)
