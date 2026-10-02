"""Step 4: เก็บบันทึกการนอนใน Supabase + ระบบสมัคร/เข้าสู่ระบบด้วยอีเมล

ตั้งค่าใน .streamlit/secrets.toml:  SUPABASE_URL, SUPABASE_KEY (publishable / anon key)
ความปลอดภัยของข้อมูลใช้ Row Level Security ใน supabase/schema.sql → แต่ละคนอ่าน/เขียนได้เฉพาะแถวของตัวเอง
"""
from datetime import date, datetime, time, timezone

from llm import _setting

try:
    from supabase import create_client
    from supabase_auth.errors import AuthApiError
except ImportError:
    create_client = None
    AuthApiError = Exception

TABLE = "sleep_logs"
ANSWER_COLS = ["sleep_latency_minutes", "number_of_night_wakeups", "bedtime_screen_time_minutes",
               "stress_score", "doomscroller"]


class DBError(Exception):
    """ข้อความในนี้แสดงให้ผู้ใช้เห็นได้เลย"""


def is_configured() -> bool:
    return create_client is not None and bool(_setting("SUPABASE_URL")) and bool(_setting("SUPABASE_KEY"))


def new_client():
    """1 ผู้ใช้ (1 session ของ Streamlit) ต้องมี client ของตัวเอง เพราะ client เก็บสถานะการล็อกอินไว้"""
    return create_client(_setting("SUPABASE_URL"), _setting("SUPABASE_KEY"))


# ---------------------------------------------------------------- auth
AUTH_MESSAGES = {
    "invalid login credentials": "อีเมลหรือรหัสผ่านไม่ถูกต้อง",
    "email not confirmed": "ยังไม่ได้ยืนยันอีเมล — เปิดลิงก์ยืนยันในอีเมลก่อน แล้วค่อยเข้าสู่ระบบ",
    "user already registered": "อีเมลนี้สมัครไว้แล้ว ลองเข้าสู่ระบบแทน",
    "password should be at least": "รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร",
    "unable to validate email": "รูปแบบอีเมลไม่ถูกต้อง",
    "rate limit": "ลองบ่อยเกินไป รอสักครู่แล้วลองใหม่",
}


def _auth_msg(e: Exception) -> str:
    text = str(getattr(e, "message", e)).lower()
    for k, v in AUTH_MESSAGES.items():
        if k in text:
            return v
    return f"เข้าสู่ระบบไม่สำเร็จ: {getattr(e, 'message', e)}"


def sign_in(client, email: str, password: str):
    try:
        res = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    except AuthApiError as e:
        raise DBError(_auth_msg(e)) from e
    except Exception as e:
        raise DBError("เชื่อมต่อ Supabase ไม่ได้ ตรวจสอบ SUPABASE_URL / อินเทอร์เน็ต") from e
    return res.user


def sign_up(client, email: str, password: str):
    """คืน (user, ต้องยืนยันอีเมลไหม)"""
    try:
        res = client.auth.sign_up({"email": email.strip(), "password": password})
    except AuthApiError as e:
        raise DBError(_auth_msg(e)) from e
    except Exception as e:
        raise DBError("เชื่อมต่อ Supabase ไม่ได้ ตรวจสอบ SUPABASE_URL / อินเทอร์เน็ต") from e
    return res.user, res.session is None


def sign_out(client):
    try:
        client.auth.sign_out()
    except Exception:
        pass


# ---------------------------------------------------------------- data
def _run(query, what: str):
    try:
        return query.execute()
    except Exception as e:
        msg = str(getattr(e, "message", e))
        if "relation" in msg and "does not exist" in msg or "Could not find the table" in msg:
            raise DBError("ยังไม่ได้สร้างตาราง — รันไฟล์ supabase/schema.sql ใน SQL Editor ก่อน") from e
        if "JWT" in msg or "expired" in msg.lower():
            raise DBError("การล็อกอินหมดอายุ กรุณาออกจากระบบแล้วเข้าใหม่") from e
        raise DBError(f"{what}ไม่สำเร็จ: {msg}") from e


def _to_entry(row: dict) -> dict:
    e = {"date": date.fromisoformat(row["date"]),
         "bed": time.fromisoformat(row["bedtime"]), "wake": time.fromisoformat(row["waketime"]),
         "hours": float(row["hours"])}
    for c in ANSWER_COLS:
        e[c] = row.get(c)
    return e


def load_entries(client) -> list[dict]:
    res = _run(client.table(TABLE).select("*").order("date"), "โหลดข้อมูล")
    return [_to_entry(r) for r in res.data]


def upsert_entry(client, entry: dict):
    row = {"date": entry["date"].isoformat(), "bedtime": entry["bed"].strftime("%H:%M"),
           "waketime": entry["wake"].strftime("%H:%M"), "hours": entry["hours"],
           **{c: entry.get(c) for c in ANSWER_COLS}, "updated_at": datetime.now(timezone.utc).isoformat()}
    _run(client.table(TABLE).upsert(row, on_conflict="user_id,date"), "บันทึก")


def delete_entry(client, d: date):
    _run(client.table(TABLE).delete().eq("date", d.isoformat()), "ลบ")


# ---------------------------------------------------------------- [schedule] เวลาการนอนที่ตั้งไว้
SCHEDULE_TABLE = "sleep_schedule"


def load_schedule(client) -> dict | None:
    """None = ยังไม่เคยตั้ง หรือยังไม่ได้สร้างตาราง (แอปจะใช้ค่าเริ่มต้นแทน)"""
    try:
        res = client.table(SCHEDULE_TABLE).select("*").limit(1).execute()
    except Exception:
        return None
    if not res.data:
        return None
    r = res.data[0]
    return {"weekday_wake": time.fromisoformat(r["weekday_wake"]), "weekend_wake": time.fromisoformat(r["weekend_wake"]),
            "target_hours": float(r["target_hours"]), "remind_before": int(r["remind_before"])}


def save_schedule(client, s: dict):
    row = {"weekday_wake": s["weekday_wake"].strftime("%H:%M"), "weekend_wake": s["weekend_wake"].strftime("%H:%M"),
           "target_hours": s["target_hours"], "remind_before": s["remind_before"],
           "updated_at": datetime.now(timezone.utc).isoformat()}
    _run(client.table(SCHEDULE_TABLE).upsert(row, on_conflict="user_id"), "บันทึกเวลานอน")
