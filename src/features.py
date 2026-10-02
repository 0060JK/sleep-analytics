"""คำถามที่ถามผู้ใช้ + วิธีแปลงคำตอบเป็น input ของโมเดล

หลักการ: ผู้ใช้ "เลือก" จากตัวเลือกแทนการพิมพ์ตัวเลขเอง และตอน train
เราแปลงข้อมูลใน dataset ให้อยู่ในรูปตัวเลือกเดียวกัน → train กับใช้งานจริงเห็นข้อมูลแบบเดียวกัน
"""
import numpy as np
import pandas as pd

TARGET = "sleep_quality_category"
CLASS_ORDER = ["Good", "Fair", "Poor"]

# แต่ละคำถาม: ตัวเลือกที่แสดง → ค่าตัวแทน (ใช้ป้อนโมเดล) และขอบเขตที่ใช้แบ่งกลุ่มข้อมูลตอน train
CHOICES = {
    "sleep_latency_minutes": {
        "label": "ใช้เวลานานแค่ไหนกว่าจะหลับ",
        "options": {"หลับเลย (<15 นาที)": 10, "15–30 นาที": 22, "30–60 นาที": 45, "เกิน 1 ชม.": 75},
        "bins": [-np.inf, 15, 30, 60, np.inf],
    },
    "number_of_night_wakeups": {
        "label": "ตื่นกลางดึกกี่ครั้ง",
        "options": {"ไม่ตื่น": 0, "1 ครั้ง": 1, "2 ครั้ง": 2, "3+ ครั้ง": 3},
        "bins": [-np.inf, 0.5, 1.5, 2.5, np.inf],
    },
    "bedtime_screen_time_minutes": {
        "label": "ก่อนนอนใช้มือถือ/จอนานแค่ไหน",
        "options": {"ไม่ได้ใช้": 0, "ไม่ถึง 30 นาที": 15, "30–60 นาที": 45, "1–2 ชม.": 90, "เกิน 2 ชม.": 150},
        "bins": [-np.inf, 5, 30, 60, 120, np.inf],
    },
    "stress_score": {
        "label": "วันนี้เครียดแค่ไหน",
        "options": {"สบายๆ": 2, "นิดหน่อย": 4, "ปานกลาง": 6, "ค่อนข้างมาก": 8, "มากที่สุด": 10},
        "bins": [-np.inf, 2.5, 4.5, 6.5, 8.5, np.inf],
    },
}
YESNO = {"doomscroller": "ไถโซเชียล/คลิปเพลินจนนอนช้ากว่าที่ตั้งใจไหม"}

NUMERIC_FEATURES = ["sleep_hours_per_night"] + list(CHOICES)
CATEGORICAL_FEATURES = list(YESNO)
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def bucketize(df: pd.DataFrame) -> pd.DataFrame:
    """แปลงค่าตัวเลขละเอียดใน dataset ให้เป็นค่าตัวแทนของตัวเลือก (ใช้ตอน train)"""
    out = df[ALL_FEATURES].copy()
    for col, q in CHOICES.items():
        values = list(q["options"].values())
        out[col] = pd.cut(out[col], bins=q["bins"], labels=values, ordered=False).astype(float)
    out["sleep_hours_per_night"] = (out["sleep_hours_per_night"] * 2).round() / 2  # ปัดเป็นครึ่งชั่วโมง
    return out
