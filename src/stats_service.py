"""คำนวณสถิติการนอนในช่วงที่เลือก (เทียบกับ stats_service ในตัวอย่าง)"""
import numpy as np
import pandas as pd


def clock(bed_min: float) -> str:
    """แปลงนาทีนับจาก 18:00 กลับเป็นเวลา HH:MM"""
    m = int(round(bed_min)) + 18 * 60
    return f"{(m // 60) % 24:02d}:{m % 60:02d}"


def calculate_statistics(df: pd.DataFrame, target_min: float):
    df = df.copy()
    df["MA7"] = df["Hours"].rolling(7, min_periods=3).mean()
    df["Diff"] = df["Hours"] - target_min
    h = df["Hours"]
    slope = float(np.polyfit(range(len(h)), h, 1)[0]) if len(h) >= 3 else 0.0
    last7 = h.tail(7)
    forecast = float(np.clip(last7.mean() + slope * 7, 0, 14)) if len(h) >= 3 else float(h.mean())
    stats = {
        "nights": len(df),
        "mean": h.mean(), "median": h.median(), "std": h.std(ddof=0),
        "min": h.min(), "max": h.max(),
        "short_nights": int((h < target_min).sum()),
        "sleep_debt": float(df["Diff"].clip(upper=0).abs().sum()),
        "bed_avg": clock(df["Bed_Min"].mean()),
        "bed_std_min": float(df["Bed_Min"].std(ddof=0)),
        "latest": h.iloc[-1], "previous": h.iloc[-2] if len(h) > 1 else np.nan,
        "ma7": df["MA7"].iloc[-1], "slope": slope, "forecast": forecast,
        "poor_share": float((df["Quality"] == "Poor").mean()),
        "good_share": float((df["Quality"] == "Good").mean()),
    }
    return stats, df


def cause_counts(df: pd.DataFrame) -> pd.Series:
    """ปัจจัยไหนถูกชี้ว่าเป็นสาเหตุบ่อยที่สุดในช่วงนี้"""
    return pd.Series([c for cs in df["Causes"] for c in cs]).value_counts()


WEEKDAYS_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"]


def weekday_average(df: pd.DataFrame) -> pd.Series:
    """ชั่วโมงนอนเฉลี่ยแยกตามวัน (วันของเช้าที่ตื่น)"""
    s = df.groupby(df["Date"].dt.weekday)["Hours"].mean()
    return s.reindex(range(7)).rename(index=dict(enumerate(WEEKDAYS_TH)))
