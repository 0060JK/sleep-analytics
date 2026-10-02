# Sleep AI (Streamlit)

## โครงสร้าง
```
sleep-ai/
├── app.py                  # หน้าเว็บ Streamlit (4 แท็บ: ภาพรวม / บันทึก / วิเคราะห์ / ถาม AI)
├── .streamlit/config.toml  # ธีมสี
├── data/                   # dataset
├── model/model.pkl         # โมเดลที่ train แล้ว (สร้างจาก src/train.py)
├── model/meta.json         # ชื่อโมเดล คะแนน และค่ามัธยฐานของคนที่นอนดี
├── src/features.py         # คำถาม 6 ข้อ + ตัวเลือก + การแปลงข้อมูล (ใช้ร่วมกันทั้งตอน train และหน้าเว็บ)
├── src/train.py            # Step 1: train + เลือกโมเดล + save
├── src/predict.py          # Step 2: โหลดโมเดล ทำนาย และหาสาเหตุ
├── src/sleep_service.py    # ข้อมูลตัวอย่าง 30 คืน + แปลงบันทึกเป็นตาราง
├── src/stats_service.py    # สถิติ: ค่าเฉลี่ย หนี้การนอน MA7 แนวโน้ม คาดการณ์
├── src/ai_service.py       # สรุปสถิติเป็นข้อความ + คำตอบสำรองจากกฎ (ใช้ตอนไม่มี key)
├── src/llm.py              # Step 3: เชื่อมต่อ Gemini (แชท + อ่านประโยคแล้วกรอกฟอร์ม)
├── src/db.py               # Step 4: Supabase — login + บันทึก/โหลด/ลบข้อมูล
├── supabase/schema.sql     # Step 4: SQL สร้างตาราง + Row Level Security
├── src/schedule.py         # [ฟีเจอร์เสริม] ตั้งเวลานอน + สร้างไฟล์ปฏิทิน .ics
├── supabase/schedule.sql   # [ฟีเจอร์เสริม] ตารางเก็บเวลานอนที่ตั้งไว้
├── .streamlit/secrets.toml.example  # ตัวอย่างไฟล์ใส่ API key
└── requirements.txt
```

## วิธีรันในเครื่อง
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/train.py              # train ใหม่ (ไม่จำเป็น เพราะมี model.pkl ให้แล้ว)
streamlit run app.py             # เปิดหน้าเว็บที่ http://localhost:8501
```

## ความคืบหน้า
- [x] Step 1: train และ save โมเดล
- [x] Step 2: หน้าเว็บแบบฟอร์ม ทำนาย บอกสาเหตุ และสรุปรายสัปดาห์
- [x] Step 2.1: ปรับหน้าตาตามต้นแบบ "นอนพอมั้ย" ลดคำถามเหลือ 6 ข้อแบบเลือกตอบ เพิ่มการตรวจคำตอบผิดปกติ
- [x] Step 2.2: เปลี่ยนหน้าตาเป็นแดชบอร์ดแบบแท็บ + กราฟ Plotly
- [x] Step 2.3: ออกแบบ UI ใหม่ (วงแหวนเป้าหมาย, กราฟช่วงเวลานอน, หน้าแชท)
- [x] Step 3: แชทกับ Gemini + พิมพ์เล่าแล้วให้ AI กรอกฟอร์ม
- [x] Step 4: เก็บข้อมูลใน Supabase + ระบบสมัคร/เข้าสู่ระบบ
- [ ] Step 5: deploy บน Streamlit Community Cloud

## ตั้งค่า Gemini (Step 3)
1. ขอ API key ฟรีที่ https://aistudio.google.com/apikey (ล็อกอินด้วยบัญชี Google → Create API key)
2. คัดลอก `.streamlit/secrets.toml.example` เป็น `.streamlit/secrets.toml` แล้ววาง key แทนข้อความตัวอย่าง
3. รัน `streamlit run app.py` → แท็บ "ถาม AI" จะขึ้นว่า "Gemini เชื่อมต่อแล้ว"

ถ้าไม่ใส่ key แอปยังใช้งานได้ แต่จะตอบจากกฎที่ตั้งไว้ และปุ่ม "ให้ AI กรอกฟอร์ม" จะกดไม่ได้
ห้าม push `secrets.toml` ขึ้น GitHub (อยู่ใน .gitignore แล้ว) — ตอน deploy ให้ใส่ key ในหน้า Secrets ของ Streamlit Cloud แทน

## ตั้งค่า Supabase (Step 4)
1. สมัคร/ล็อกอินที่ https://supabase.com → New project (ตั้งชื่อ, รหัสผ่าน database, Region: Southeast Asia (Singapore))
2. เมนูซ้าย SQL Editor → New query → วางเนื้อหาไฟล์ `supabase/schema.sql` ทั้งไฟล์ → Run
3. Project Settings → API (Data API / API Keys) → คัดลอก Project URL และ publishable key (หรือ anon key) ใส่ใน `.streamlit/secrets.toml`
4. (ช่วงพัฒนา) Authentication → Sign In / Providers → Email → ปิด "Confirm email" จะได้สมัครแล้วเข้าได้ทันที
5. รัน `streamlit run app.py` → จะเจอหน้าเข้าสู่ระบบ

ห้ามใช้ secret key / service_role key ในแอปนี้ — ใช้ publishable/anon key เท่านั้น (ความปลอดภัยมาจาก Row Level Security)
ถ้าไม่ใส่ค่า Supabase แอปจะทำงานแบบเดิม (ข้อมูลอยู่แค่ในหน้าเว็บ)

## ฟีเจอร์เสริม: ตั้งเวลานอน + แจ้งเตือน
- รัน `supabase/schedule.sql` ใน SQL Editor เพิ่ม (ครั้งเดียว) เพื่อให้จำเวลาที่ตั้งไว้ข้ามการล็อกอิน
- ปิดฟีเจอร์: แก้ `FEATURE_SCHEDULE = False` ใน app.py
- เอาออกถาวร: ลบ `src/schedule.py`, `supabase/schedule.sql`, ส่วนที่มีป้าย `[schedule]` ใน app.py และ db.py แล้วรัน `drop table public.sleep_schedule;` ใน Supabase
