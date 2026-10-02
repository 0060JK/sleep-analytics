"""Step 2: โหลดโมเดล ทำนาย และหาสาเหตุ (แยกจากหน้าเว็บ เพื่อให้ step 3 ส่งผลต่อให้ LLM ได้)"""
from datetime import datetime, timedelta
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from features import ALL_FEATURES

ROOT = Path(__file__).resolve().parents[1]

AGE_GROUPS = {"ต่ำกว่า 18 ปี": (8.0, 10.0), "18–64 ปี": (7.0, 9.0), "65 ปีขึ้นไป": (7.0, 8.0)}

# ถ้าปรับปัจจัยนี้เป็น "แบบคนที่นอนดี" แล้วโอกาสนอนแย่ลดลงเท่าไร
WHAT_IF = {
    "doomscroller": ("ไถโซเชียลจนนอนช้า", lambda u, ref: "No"),
    "bedtime_screen_time_minutes": ("ใช้จอก่อนนอนนาน", lambda u, ref: min(u, 15)),
    "sleep_latency_minutes": ("ใช้เวลานานกว่าจะหลับ", lambda u, ref: min(u, 10)),
    "number_of_night_wakeups": ("ตื่นกลางดึกบ่อย", lambda u, ref: min(u, 1)),
    "stress_score": ("ความเครียด", lambda u, ref: min(u, 4)),
    "sleep_hours_per_night": ("นอนน้อยเกินไป", lambda u, ref: max(u, ref["target_min"])),
}


def load_model():
    model = joblib.load(ROOT / "model" / "model.pkl")
    meta = json.loads((ROOT / "model" / "meta.json").read_text())
    return model, meta


def sleep_duration(bedtime, waketime) -> float:
    """คำนวณชั่วโมงนอนจากเวลาเข้านอน/ตื่น (รองรับการนอนข้ามเที่ยงคืน)"""
    b = datetime.combine(datetime.today(), bedtime)
    w = datetime.combine(datetime.today(), waketime)
    if w <= b:
        w += timedelta(days=1)
    return round((w - b).total_seconds() / 3600, 1)


def check_input(bedtime, hours: float) -> list[str]:
    """ตรวจคำตอบที่ดูผิดปกติ — ให้ผู้ใช้ยืนยันก่อนบันทึก"""
    warnings = []
    if hours < 3:
        warnings.append(f"คำนวณได้ว่านอนแค่ {hours} ชม.")
    if hours > 13:
        warnings.append(f"คำนวณได้ว่านอนถึง {hours} ชม.")
    if 8 <= bedtime.hour < 18:
        warnings.append(f"เวลาเข้านอน {bedtime.strftime('%H:%M')} เป็นช่วงกลางวัน — ใส่เวลาแบบ 24 ชม. ถูกไหม (เช่น 5 ทุ่ม = 23:00)")
    return warnings


def verdict(hours: float, lo: float, hi: float) -> tuple[str, str]:
    if hours < lo - 1:
        return "bad", "นอนไม่พอ"
    if hours < lo:
        return "warn", "ไม่ค่อยพอ"
    if hours <= hi:
        return "good", "เพียงพอ"
    return "warn", "นอนนานกว่าปกติ"


def _frame(user: dict) -> pd.DataFrame:
    return pd.DataFrame([{k: (np.nan if user.get(k) is None else user.get(k)) for k in ALL_FEATURES}])


def predict(model, user: dict) -> dict:
    proba = model.predict_proba(_frame(user))[0]
    probs = {c: float(p) for c, p in zip(model.classes_, proba)}
    return {"label": max(probs, key=probs.get), "probabilities": probs}


def likely_causes(model, user: dict, target_min: float, top_n: int = 3) -> list[dict]:
    """ลองเปลี่ยนทีละปัจจัยให้เป็นแบบคนนอนดี แล้วดูว่าโอกาส 'นอนแย่' ลดลงแค่ไหน"""
    base = predict(model, user)["probabilities"]["Poor"]
    ref = {"target_min": target_min}
    out = []
    for col, (name, improve) in WHAT_IF.items():
        if user.get(col) is None:
            continue
        better = improve(user[col], ref)
        if better == user[col]:
            continue
        gain = base - predict(model, {**user, col: better})["probabilities"]["Poor"]
        if gain > 0.02:
            out.append({"factor": name, "gain": gain})
    return sorted(out, key=lambda c: c["gain"], reverse=True)[:top_n]


def weekly_trend(hours: list[float]) -> float | None:
    """ความชัน (ชม./คืน) ของชั่วโมงนอน 7 คืนล่าสุด — ใช้คาดแนวโน้มสัปดาห์หน้าแบบง่าย"""
    if len(hours) < 3:
        return None
    return float(np.polyfit(range(len(hours)), hours, 1)[0])
