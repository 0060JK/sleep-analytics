"""จัดการข้อมูลการนอน (เทียบกับ gold_service ในตัวอย่าง): ข้อมูลตัวอย่าง + แปลงเป็น DataFrame"""
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from features import CHOICES
from predict import likely_causes, predict, sleep_duration


def _snap(value, options):
    """เลือกตัวเลือกที่ใกล้ค่าที่สุด (ให้ข้อมูลตัวอย่างอยู่ในรูปเดียวกับที่ผู้ใช้กรอก)"""
    opts = list(options.values())
    return min(opts, key=lambda o: abs(o - value))


def sample_entries(n_days: int = 30, seed: int = 7) -> list[dict]:
    """ข้อมูลตัวอย่าง 30 คืน — นักศึกษาที่ช่วงหลังเริ่มนอนดึกขึ้น"""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_days):
        d = date.today() - timedelta(days=n_days - 1 - i)
        late = 0.6 * i / n_days + (0.7 if d.weekday() in (4, 5) else 0)   # ดึกขึ้นเรื่อยๆ + ศ/ส ดึกกว่า
        doom = rng.random() < 0.35 + 0.4 * i / n_days
        bed_min = int(23 * 60 + 20 + 60 * (late + rng.normal(0, 0.45)) + (40 if doom else 0))
        bed_min = (bed_min // 5) * 5
        wake_min = int(7 * 60 + 5 + rng.normal(0, 18) + (60 if d.weekday() in (5, 6) else 0))
        wake_min = (wake_min // 5) * 5
        bed = time((bed_min // 60) % 24, bed_min % 60)
        wake = time((wake_min // 60) % 24, wake_min % 60)
        screen = 25 + (70 if doom else 0) + rng.normal(0, 20)
        out.append({
            "date": d, "bed": bed, "wake": wake, "hours": sleep_duration(bed, wake),
            "sleep_latency_minutes": _snap(15 + (20 if doom else 0) + rng.normal(0, 10),
                                           CHOICES["sleep_latency_minutes"]["options"]),
            "number_of_night_wakeups": _snap(max(rng.normal(0.8 + (0.8 if doom else 0), 0.7), 0),
                                             CHOICES["number_of_night_wakeups"]["options"]),
            "bedtime_screen_time_minutes": _snap(screen, CHOICES["bedtime_screen_time_minutes"]["options"]),
            "stress_score": _snap(4 + 3 * i / n_days + rng.normal(0, 1.5), CHOICES["stress_score"]["options"]),
            "doomscroller": "Yes" if doom else "No",
            "sample": True,
        })
    return out


def model_input(e: dict) -> dict:
    keys = ["sleep_latency_minutes", "number_of_night_wakeups", "bedtime_screen_time_minutes",
            "stress_score", "doomscroller"]
    return {"sleep_hours_per_night": e["hours"], **{k: e.get(k) for k in keys}}


def bedtime_minutes(t: time) -> int:
    """นาทีนับจาก 18:00 — ให้ 23:00 กับ 01:00 เรียงต่อกันถูกต้องบนกราฟ"""
    m = t.hour * 60 + t.minute
    return m - 18 * 60 if m >= 18 * 60 else m + 6 * 60


def to_frame(entries: list[dict], model, target_min: float) -> pd.DataFrame:
    rows = []
    for e in sorted(entries, key=lambda x: x["date"]):
        x = model_input(e)
        res = predict(model, x)
        causes = likely_causes(model, x, target_min)
        rows.append({
            "Date": pd.Timestamp(e["date"]), "Bedtime": e["bed"], "Wake": e["wake"], "Hours": e["hours"],
            "Bed_Min": bedtime_minutes(e["bed"]), "Quality": res["label"],
            "P_Good": res["probabilities"]["Good"], "P_Poor": res["probabilities"]["Poor"],
            "Causes": [c["factor"] for c in causes], "Raw": e,
        })
    return pd.DataFrame(rows)
