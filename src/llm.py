"""Step 3: เชื่อมต่อ Gemini

ใช้ 2 งาน
1. chat_stream()        ตอบคำถามในหน้าแชท โดยส่ง "สถิติสรุป" ไปเป็นบริบท (ไม่ส่งข้อมูลดิบทุกแถว)
2. extract_sleep_log()  อ่านประโยคที่ผู้ใช้เล่า แล้วดึงเป็นคำตอบของฟอร์ม (JSON ตาม schema)

API key อ่านจาก .streamlit/secrets.toml (GEMINI_API_KEY) หรือ environment variable ชื่อเดียวกัน
"""
import os
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from features import CHOICES

try:
    from google import genai
    from google.genai import errors, types
except ImportError:          # ยังไม่ได้ pip install google-genai → แอปยังใช้งานได้ในโหมดออฟไลน์
    genai = None

# ลองโมเดลตามลำดับ ถ้าตัวแรกไม่มี/ถูกปิด จะขยับไปตัวถัดไปเอง (ชื่อโมเดลของ Google เปลี่ยนบ่อย)
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]

SYSTEM_PROMPT = """คุณคือ "ผู้ช่วยการนอน" ในแอป นอนพอมั้ย ตอบเป็นภาษาไทย สุภาพ เป็นกันเอง กระชับ
กฎ:
- ใช้เฉพาะข้อมูลในส่วน [ข้อมูลการนอนของผู้ใช้] เวลาอ้างถึงตัวเลขให้ใช้ตัวเลขจริงจากข้อมูล ห้ามแต่งตัวเลขเอง
- ถ้าข้อมูลไม่พอจะตอบ ให้บอกตรงๆ และแนะนำว่าควรบันทึกอะไรเพิ่ม
- คำแนะนำต้องทำได้จริงและเจาะจง เช่น เวลาที่ควรเข้านอน หรือสิ่งที่ควรเลิกทำก่อนนอน
- "ปัจจัยที่พบบ่อย" มาจากโมเดล ML ที่ประเมินจากข้อมูลสำรวจ เป็นความสัมพันธ์ ไม่ใช่การพิสูจน์ว่าเป็นสาเหตุแน่นอน
- คุณไม่ใช่แพทย์ ห้ามวินิจฉัยโรค ถ้าผู้ใช้พูดถึงอาการอย่างนอนไม่หลับเรื้อรังหลายสัปดาห์ กรนหนักจนหยุดหายใจ
  หรือง่วงจนเป็นอันตรายตอนขับรถ ให้แนะนำให้ปรึกษาแพทย์
- ตอบไม่เกิน 150 คำ ใช้ bullet ได้ถ้าช่วยให้อ่านง่าย
- ถ้าถูกถามเรื่องที่ไม่เกี่ยวกับการนอนหรือสุขภาพการนอน ให้ตอบสั้นๆ แล้วชวนกลับมาที่เรื่องการนอน"""


class LLMUnavailable(Exception):
    """ไม่มี key / ไม่มี library / เรียก API ไม่สำเร็จ — ให้แอปถอยกลับไปใช้คำตอบจากกฎ"""


def _setting(name: str, default=None):
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:          # ไม่มีไฟล์ secrets.toml
        pass
    return os.environ.get(name, default)


def get_client():
    key = _setting("GEMINI_API_KEY")
    if genai is None or not key:
        return None
    return genai.Client(api_key=key)


def _models():
    custom = _setting("GEMINI_MODEL")
    return [custom] + [m for m in DEFAULT_MODELS if m != custom] if custom else DEFAULT_MODELS


def _friendly(e: Exception) -> str:
    code = getattr(e, "code", None)
    if code == 429:
        return "ใช้ Gemini ครบโควตาแล้ว รอสักครู่แล้วลองใหม่"
    if code in (400, 401, 403):
        return "API key ไม่ถูกต้องหรือไม่มีสิทธิ์ใช้โมเดลนี้ ตรวจสอบ GEMINI_API_KEY อีกครั้ง"
    return f"เรียก Gemini ไม่สำเร็จ ({code or type(e).__name__})"


def _call(client, fn, **kwargs):
    """เรียก API โดยลองไล่โมเดล ถ้าเจอ 404 (ไม่มีโมเดลนี้) ให้ลองตัวถัดไป"""
    last = None
    for model in _models():
        try:
            return fn(model=model, **kwargs)
        except errors.APIError as e:
            last = e
            if e.code == 404:
                continue
            raise LLMUnavailable(_friendly(e)) from e
    raise LLMUnavailable(_friendly(last)) from last


# ---------------------------------------------------------------- แชท
def chat_stream(client, history: list[tuple[str, str]], question: str, context: str):
    """คืน generator ของข้อความทีละท่อน (ใช้กับ st.write_stream)"""
    contents = [types.Content(role="user", parts=[types.Part.from_text(
        text=f"[ข้อมูลการนอนของผู้ใช้]\n{context}\n\nรับทราบข้อมูลแล้วรอคำถาม")]),
        types.Content(role="model", parts=[types.Part.from_text(text="รับทราบครับ")])]
    for role, text in history[-8:]:                     # ส่งประวัติแชทล่าสุด 8 ข้อความพอ ประหยัด token
        clean = re.sub(r"<[^>]+>", "", text)
        contents.append(types.Content(role="user" if role == "user" else "model",
                                      parts=[types.Part.from_text(text=clean)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4,
                                         max_output_tokens=800)
    stream = _call(client, client.models.generate_content_stream, contents=contents, config=config)

    def gen():
        try:
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except errors.APIError as e:
            yield f"\n\n_({_friendly(e)})_"
    return gen()


# ---------------------------------------------------------------- ดึงข้อมูลจากประโยค
def _options(col):
    return Literal[tuple(CHOICES[col]["options"])]


class SleepLog(BaseModel):
    bedtime: Optional[str] = Field(None, description="เวลาเข้านอน 24 ชม. รูปแบบ HH:MM เช่น ตีสอง = 02:00, 5 ทุ่ม = 23:00")
    waketime: Optional[str] = Field(None, description="เวลาตื่น 24 ชม. รูปแบบ HH:MM")
    bedtime_screen_time_minutes: Optional[_options("bedtime_screen_time_minutes")] = None
    doomscroller: Optional[Literal["ใช่", "ไม่ใช่"]] = Field(None, description="ไถโซเชียล/คลิปเพลินจนนอนช้ากว่าที่ตั้งใจหรือไม่")
    stress_score: Optional[_options("stress_score")] = None
    sleep_latency_minutes: Optional[_options("sleep_latency_minutes")] = None
    number_of_night_wakeups: Optional[_options("number_of_night_wakeups")] = None
    note: str = Field("", description="ประโยคสั้นๆ อธิบายการตีความที่ไม่ชัดเจน หรือสตริงว่าง")


EXTRACT_PROMPT = """ข้อความต่อไปนี้คือสิ่งที่ผู้ใช้เล่าถึงการนอนเมื่อคืน:
\"\"\"{text}\"\"\"
ดึงข้อมูลตาม schema ใส่ค่าเฉพาะเรื่องที่ผู้ใช้พูดถึงหรืออนุมานได้ชัดเจน เรื่องไหนไม่ได้พูดถึงให้เป็น null ห้ามเดา
ตัวเลือกต้องตรงกับที่ schema กำหนดทุกตัวอักษร"""


def _norm_time(v):
    if not v:
        return None
    m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*", str(v))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mi:02d}" if 0 <= h <= 23 and 0 <= mi <= 59 else None


def extract_sleep_log(client, text: str) -> dict:
    config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=SleepLog,
                                         temperature=0)
    resp = _call(client, client.models.generate_content, contents=EXTRACT_PROMPT.format(text=text), config=config)
    try:
        data = SleepLog.model_validate_json(resp.text).model_dump()
    except Exception as e:
        raise LLMUnavailable("อ่านคำตอบจาก Gemini ไม่ได้ ลองพิมพ์ใหม่อีกครั้ง") from e
    data["bedtime"], data["waketime"] = _norm_time(data["bedtime"]), _norm_time(data["waketime"])
    return data
