"""นอนพอมั้ย — Sleep AI   รัน:  streamlit run app.py"""
import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).parent / "src"))
from features import CHOICES, YESNO  # noqa: E402
from predict import AGE_GROUPS, check_input, load_model, sleep_duration, verdict  # noqa: E402
from sleep_service import sample_entries, to_frame  # noqa: E402
from stats_service import calculate_statistics, cause_counts, clock, weekday_average  # noqa: E402
from ai_service import ask_sleep_ai, build_context  # noqa: E402
from llm import LLMUnavailable, chat_stream, extract_sleep_log, get_client  # noqa: E402

st.set_page_config(page_title="นอนพอมั้ย", page_icon="🌙", layout="wide", initial_sidebar_state="collapsed")

# =========================================================
# ธีมกลางคืน: สี + ฟอนต์เดิม, layout แบบแอปสุขภาพ (การ์ดโค้งมน, แท็บแบบเม็ดยา)
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap');
:root{
  --bg:#07080f; --surface:#0f111c; --surface2:#151827; --border:#252a40;
  --accent:#8b7cf6; --accent2:#6d5ce8; --green:#16c784; --amber:#f5b942; --danger:#ea3943;
  --text:#f4f5fb; --muted:#8f93ab;
}
html, body, [class*="css"], .stApp, button, input, textarea { font-family:'IBM Plex Sans Thai', Inter, sans-serif; }
.stApp{
  color:var(--text);
  background:
    radial-gradient(1200px 520px at 85% -10%, rgba(139,124,246,.22), transparent 60%),
    radial-gradient(900px 480px at -10% 10%, rgba(54,74,168,.20), transparent 60%),
    radial-gradient(1.2px 1.2px at 12% 18%, rgba(255,255,255,.7), transparent 60%),
    radial-gradient(1px 1px at 28% 8%, rgba(255,255,255,.55), transparent 60%),
    radial-gradient(1.4px 1.4px at 46% 22%, rgba(255,255,255,.6), transparent 60%),
    radial-gradient(1px 1px at 63% 12%, rgba(255,255,255,.5), transparent 60%),
    radial-gradient(1.3px 1.3px at 78% 28%, rgba(255,255,255,.6), transparent 60%),
    radial-gradient(1px 1px at 92% 6%, rgba(255,255,255,.5), transparent 60%),
    linear-gradient(180deg, #0b0d1c 0%, #07080f 55%);
  background-attachment:fixed;
}
[data-testid="stHeader"]{background:transparent;height:0}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none}
#MainMenu, footer{visibility:hidden}
.block-container{max-width:1180px;padding-top:2rem;padding-bottom:4rem}

/* ---------- หัวเว็บแบบทักทาย ---------- */
.greet{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.greet-hi{color:var(--muted);font-size:.95rem}
.greet-title{font-size:2rem;font-weight:700;line-height:1.25;margin-top:2px}
.greet-title em{font-style:normal;color:var(--accent)}
.chip{display:inline-flex;align-items:center;gap:7px;font-size:.78rem;font-weight:600;color:var(--muted);
  background:rgba(21,24,39,.8);border:1px solid var(--border);border-radius:99px;padding:6px 12px}
.dot{width:7px;height:7px;border-radius:50%}
.dot.live{background:var(--green)} .dot.demo{background:var(--amber)}

/* ---------- แท็บแบบเม็ดยา ---------- */
[data-testid="stTabs"] [role="tablist"]{gap:6px;background:rgba(15,17,28,.85);border:1px solid var(--border)!important;
  border-radius:99px;padding:5px;width:fit-content;max-width:100%;overflow-x:auto;box-shadow:none!important}
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] [role="tablist"]::before{display:none!important}
[data-testid="stTab"]{border-radius:99px!important;padding:8px 18px!important;font-weight:600!important;
  color:#a3a7bd!important;background:transparent!important;border:0!important;box-shadow:none!important;height:auto!important}
[data-testid="stTab"]:hover{color:#fff!important}
[data-testid="stTab"][aria-selected="true"]{background:var(--accent)!important;color:#fff!important}
[data-testid="stTab"] *{color:inherit!important}
[data-testid="stTab"]::after, [data-testid="stTab"]::before{display:none!important}
[data-testid="stTabs"] .react-aria-SelectionIndicator{display:none!important}
[data-testid="stTabs"] [role="tabpanel"]{padding-top:22px}

/* ---------- การ์ด ---------- */
.card{background:rgba(15,17,28,.88);border:1px solid var(--border);border-radius:20px;padding:20px 22px;height:100%}
.card-title{font-size:.82rem;color:var(--muted);font-weight:600;margin-bottom:10px}
.tile{display:flex;gap:14px;align-items:center;background:rgba(15,17,28,.88);border:1px solid var(--border);
  border-radius:18px;padding:16px 18px}
.icon{flex:none;width:42px;height:42px;border-radius:14px;display:grid;place-items:center;font-size:1.15rem;
  background:rgba(139,124,246,.14);color:var(--accent)}
.icon.g{background:rgba(22,199,132,.14);color:var(--green)} .icon.a{background:rgba(245,185,66,.14);color:var(--amber)}
.icon.r{background:rgba(234,57,67,.14);color:var(--danger)}
.tile-val{font-size:1.35rem;font-weight:700;line-height:1.2}
.tile-lbl{font-size:.8rem;color:var(--muted)}
.pill{display:inline-block;font-size:.76rem;font-weight:700;padding:4px 11px;border-radius:99px}
.pill.good{background:rgba(22,199,132,.16);color:var(--green)}
.pill.warn{background:rgba(245,185,66,.16);color:var(--amber)}
.pill.bad{background:rgba(234,57,67,.16);color:var(--danger)}
.muted{color:var(--muted);font-size:.86rem;line-height:1.6}
.h-sec{font-size:1.05rem;font-weight:700;margin:26px 0 12px}

/* วงแหวนเป้าหมาย + แถบช่วงเวลาหลับ */
.hero{display:flex;gap:28px;align-items:center;flex-wrap:wrap}
.ring-num{font-size:30px;font-weight:700;fill:#fff}
.ring-sub{font-size:12px;fill:#8f93ab}
.window{position:relative;height:38px;background:rgba(21,24,39,.9);border-radius:12px;margin:10px 0 6px;overflow:hidden}
.window .seg{position:absolute;top:6px;bottom:6px;border-radius:9px;
  background:linear-gradient(90deg,#6d5ce8,#8b7cf6);box-shadow:0 0 18px rgba(139,124,246,.45)}
.window .target{position:absolute;top:0;bottom:0;border-left:1px dashed rgba(22,199,132,.6);border-right:1px dashed rgba(22,199,132,.6);
  background:rgba(22,199,132,.06)}
.axis{display:flex;justify-content:space-between;color:var(--muted);font-size:.72rem}

/* insight list */
.insight{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #1d2135}
.insight:last-child{border-bottom:0}
.insight b{color:#fff}

/* ฟอร์มบันทึก */
.step{display:flex;align-items:center;gap:10px;font-weight:700;margin:6px 0 4px}
.step span{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:.8rem;
  background:var(--accent);color:#fff}
.preview{border-radius:16px;padding:14px 16px;background:linear-gradient(135deg,rgba(109,92,232,.25),rgba(15,17,28,.9));
  border:1px solid rgba(139,124,246,.35)}
.night{display:flex;align-items:center;gap:14px;padding:11px 14px;border-radius:14px;background:rgba(21,24,39,.75);margin-bottom:8px}
.night .d{width:62px;color:var(--muted);font-size:.82rem}
.night .bar{flex:1;height:8px;border-radius:99px;background:#1d2135;position:relative;overflow:hidden}
.night .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:99px}
.night .h{width:58px;text-align:right;font-weight:600}

/* ปุ่ม */
.stButton > button, .stFormSubmitButton > button{border-radius:99px;min-height:40px;border:1px solid var(--border);
  background:var(--surface2);color:#fff;font-weight:600}
.stButton > button:hover{border-color:var(--accent);color:#fff}
.stButton > button[kind="primary"]{background:var(--accent);border-color:var(--accent)}
.stButton > button[kind="primary"]:hover{background:var(--accent2);border-color:var(--accent2)}
[data-testid="stChatMessage"]{background:rgba(15,17,28,.75);border:1px solid var(--border);border-radius:18px}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:14px;overflow:hidden}
</style>
""", unsafe_allow_html=True)

COLORS = {"good": "#16c784", "warn": "#f5b942", "bad": "#ea3943"}
QUALITY_TH = {"Good": ("good", "ดี"), "Fair": ("warn", "พอใช้"), "Poor": ("bad", "แย่")}
TH_MONTH = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
DAY_SHORT = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
CHART = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             font=dict(color="#a2a6bd", family="IBM Plex Sans Thai"), margin=dict(l=8, r=8, t=8, b=8),
             xaxis=dict(showgrid=False, zeroline=False, tickformat="%d/%m"), showlegend=False)


@st.cache_resource
def get_model():
    return load_model()


model, meta = get_model()
llm = get_client()            # None = ยังไม่ได้ใส่ GEMINI_API_KEY → ใช้คำตอบจากกฎแทน
ss = st.session_state
ss.setdefault("entries", sample_entries())
ss.setdefault("pending", None)
ss.setdefault("age_group", "18–64 ปี")
ss.setdefault("chat", [])
ss.setdefault("ask", None)
ss.setdefault("f_bed", time(23, 30))
ss.setdefault("f_wake_t", time(7, 0))
lo, hi = AGE_GROUPS[ss.age_group]
is_demo = any(e.get("sample") for e in ss.entries)


# ---------- helpers ----------
def th_date(d):
    return f"{d.day} {TH_MONTH[d.month]}"


def hrs(v):
    return "–" if pd.isna(v) else f"{v:.1f} ชม."


def tile(icon, value, label, tone=""):
    return (f'<div class="tile"><div class="icon {tone}">{icon}</div>'
            f'<div><div class="tile-val">{value}</div><div class="tile-lbl">{label}</div></div></div>')


def ring(hours, target):
    """วงแหวน: นอนได้กี่ % ของเป้าหมาย"""
    pct = max(0.0, min(hours / target, 1.0))
    r, c = 62, 2 * 3.1416 * 62
    color = COLORS[verdict(hours, lo, hi)[0]]
    return f"""<svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx="80" cy="80" r="{r}" fill="none" stroke="#1d2135" stroke-width="14"/>
      <circle cx="80" cy="80" r="{r}" fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round"
        stroke-dasharray="{c * pct:.1f} {c:.1f}" transform="rotate(-90 80 80)"/>
      <text x="80" y="80" text-anchor="middle" class="ring-num">{hours:.1f}</text>
      <text x="80" y="102" text-anchor="middle" class="ring-sub">{pct:.0%} ของเป้า {target:.0f} ชม.</text></svg>"""


def sleep_window(bed_min, hours):
    """แถบช่วงเวลาหลับบนแกน 20:00 → 12:00 (16 ชม.) — bed_min = นาทีนับจาก 18:00"""
    start = (bed_min - 120) / 960 * 100
    width = hours * 60 / 960 * 100
    t0, t1 = (22 * 60 + 0 - 20 * 60) / 960 * 100, 9 * 60 / 960 * 100  # ช่วงแนะนำ: เข้านอน 22:00 + 9 ชม.
    return (f'<div class="window"><div class="target" style="left:{t0:.1f}%;width:{t1:.1f}%"></div>'
            f'<div class="seg" style="left:{max(start, 0):.1f}%;width:{width:.1f}%"></div></div>'
            '<div class="axis"><span>20:00</span><span>00:00</span><span>04:00</span><span>08:00</span><span>12:00</span></div>')


def range_picker(key):
    p = st.segmented_control("ช่วงเวลา", ["7 คืน", "14 คืน", "30 คืน"], default="30 คืน", key=key,
                             label_visibility="collapsed") or "30 คืน"
    return p, int(p.split()[0])


def save(entry):
    ss.entries = [e for e in ss.entries if e["date"] != entry["date"]] + [entry]
    ss.pending = None
    ss.just_saved = entry["date"]


# ---------- หัวเว็บ ----------
now = datetime.now(ZoneInfo("Asia/Bangkok"))
hello = ("อรุณสวัสดิ์" if 5 <= now.hour < 12 else "สวัสดีตอนบ่าย" if now.hour < 17
         else "สวัสดีตอนเย็น" if now.hour < 21 else "ใกล้เวลานอนแล้ว")
df_all = to_frame(ss.entries, model, lo) if ss.entries else pd.DataFrame()
if len(df_all):
    k_last, lbl_last = verdict(df_all["Hours"].iloc[-1], lo, hi)
    headline = f"เมื่อคืนคุณ<em>{lbl_last}</em>"
else:
    headline = "เริ่มบันทึกการนอนคืนแรกกัน"
status = (f'<span class="dot demo"></span>ข้อมูลตัวอย่าง {len(ss.entries)} คืน' if is_demo
          else f'<span class="dot live"></span>ข้อมูลของคุณ {len(ss.entries)} คืน')
st.markdown(f"""<div class="greet">
  <div><div class="greet-hi">☾ นอนพอมั้ย · {hello}</div><div class="greet-title">{headline}</div></div>
  <div class="chip">{status} · เป้าหมาย {lo:.0f}–{hi:.0f} ชม.</div></div>""", unsafe_allow_html=True)

tabs = st.tabs(["ภาพรวม", "บันทึกการนอน", "วิเคราะห์", "ถาม AI"])

# =========================================================
# ภาพรวม
# =========================================================
with tabs[0]:
    if len(df_all) < 2:
        st.info("บันทึกอย่างน้อย 2 คืนในแท็บ **บันทึกการนอน** เพื่อดูภาพรวม")
    else:
        last = df_all.iloc[-1]
        k, lbl = verdict(last["Hours"], lo, hi)
        qk, qth = QUALITY_TH[last["Quality"]]
        avg7 = df_all["Hours"].tail(8).iloc[:-1].mean()
        diff = (last["Hours"] - avg7) * 60
        causes = last["Causes"]
        c1, c2 = st.columns([1.35, 1], gap="medium")
        with c1:
            st.markdown(f"""<div class="card"><div class="card-title">คืนล่าสุด · {th_date(last["Date"])}</div>
              <div class="hero">{ring(last["Hours"], lo)}
                <div style="flex:1;min-width:220px">
                  <div><span class="pill {k}">{lbl}</span>&nbsp;<span class="pill {qk}">คุณภาพ: {qth}</span></div>
                  <div class="muted" style="margin-top:10px">หลับ <b style="color:#fff">{last["Bedtime"]:%H:%M}</b> → ตื่น
                    <b style="color:#fff">{last["Wake"]:%H:%M}</b> · {'มากกว่า' if diff >= 0 else 'น้อยกว่า'}ค่าเฉลี่ย 7 คืนก่อน
                    {abs(diff):.0f} นาที</div>
                  {sleep_window(last["Bed_Min"], last["Hours"])}
                </div></div></div>""", unsafe_allow_html=True)
        with c2:
            if causes:
                items = "".join(f'<div class="insight"><div class="icon a">!</div><div><b>{c}</b>'
                                f'<div class="muted">ถ้าปรับได้ คืนต่อไปมีแนวโน้มหลับดีขึ้น</div></div></div>' for c in causes)
            else:
                items = ('<div class="insight"><div class="icon g">✓</div><div><b>ไม่พบปัจจัยเสี่ยงเด่น</b>'
                         '<div class="muted">รักษารูปแบบนี้ไว้ได้เลย</div></div></div>')
            st.markdown(f'<div class="card"><div class="card-title">อะไรทำให้เมื่อคืนเป็นแบบนี้</div>{items}</div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="h-sec">สัปดาห์นี้ของคุณ</div>', unsafe_allow_html=True)
        stats7, _ = calculate_statistics(df_all.tail(7), lo)
        t1, t2, t3, t4 = st.columns(4)
        t1.markdown(tile("◷", hrs(stats7["mean"]), "นอนเฉลี่ยต่อคืน", "g" if stats7["mean"] >= lo else "a"), unsafe_allow_html=True)
        t2.markdown(tile("▼", hrs(stats7["sleep_debt"]), "หนี้การนอนสะสม", "r" if stats7["sleep_debt"] > 3 else "a"), unsafe_allow_html=True)
        t3.markdown(tile("☾", stats7["bed_avg"], f"เข้านอนเฉลี่ย (±{stats7['bed_std_min']:.0f} นาที)"), unsafe_allow_html=True)
        sl = stats7["slope"] * 60
        t4.markdown(tile("↗" if sl >= 0 else "↘", f"{sl:+.0f} นาที", "แนวโน้มต่อคืน", "g" if sl >= 0 else "r"), unsafe_allow_html=True)

        h1, h2 = st.columns([3, 1])
        h1.markdown('<div class="h-sec">ช่วงเวลาที่หลับแต่ละคืน</div>', unsafe_allow_html=True)
        with h2:
            st.write("")
            period, n = range_picker("overview_range")
        _, df = calculate_statistics(df_all.tail(n), lo)
        # กราฟ "หน้าต่างการนอน": แท่งลอยจากเวลาเข้านอนถึงเวลาตื่น
        fig = go.Figure(go.Bar(
            x=df["Date"], base=df["Bed_Min"], y=df["Hours"] * 60,
            marker=dict(color=[COLORS[verdict(h, lo, hi)[0]] for h in df["Hours"]], cornerradius=6),
            customdata=list(zip(df["Bedtime"].map(lambda t: t.strftime("%H:%M")),
                                df["Wake"].map(lambda t: t.strftime("%H:%M")), df["Hours"])),
            hovertemplate="%{x|%d/%m}<br>%{customdata[0]} → %{customdata[1]}<br><b>%{customdata[2]:.1f} ชม.</b><extra></extra>"))
        end = df["Bed_Min"] + df["Hours"] * 60
        y_top, y_bot = (df["Bed_Min"].min() // 60) * 60 - 30, (end.max() // 60 + 1) * 60 + 30
        ticks = list(range(int(y_top) + 30, int(y_bot), 60))
        fig.update_layout(height=380, bargap=0.35, **CHART, yaxis=dict(
            autorange=False, range=[y_bot, y_top],
            tickvals=ticks, ticktext=[clock(t) for t in ticks], gridcolor="#1a1e31", zeroline=False))
        with st.container(border=True):
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.caption("แต่ละแท่ง = ตั้งแต่เข้านอนจนตื่น · สีเขียว/เหลือง/แดง = นอนพอ / ไม่ค่อยพอ / ไม่พอ")

# =========================================================
# บันทึกการนอน
# =========================================================
with tabs[1]:
    left, right = st.columns([1.15, 1], gap="large")
    with left, st.container(border=True):
        # ---- ทางลัด: พิมพ์เล่าแล้วให้ Gemini กรอกฟอร์มให้ (ต้องอยู่ก่อน widget ของฟอร์ม เพื่อเซ็ตค่าได้)
        with st.expander("✍️ ขี้เกียจกด? พิมพ์เล่าแล้วให้ AI กรอกให้", expanded=False):
            story = st.text_area("เล่าการนอนเมื่อคืน", key="story", height=90, label_visibility="collapsed",
                                 placeholder="เช่น เมื่อคืนไถติ๊กต็อกจนตีสอง ตื่น 7 โมงครึ่ง กว่าจะหลับก็นาน ตื่นมาฉี่ 1 รอบ งานเยอะเครียดมาก")
            if st.button("ให้ AI กรอกฟอร์ม", width="stretch", disabled=llm is None):
                if story.strip():
                    try:
                        with st.spinner("Gemini กำลังอ่าน..."):
                            got = extract_sleep_log(llm, story)
                        filled = []
                        if got["bedtime"]:
                            ss.f_bed = time.fromisoformat(got["bedtime"]); filled.append("เวลาเข้านอน")
                        if got["waketime"]:
                            ss.f_wake_t = time.fromisoformat(got["waketime"]); filled.append("เวลาตื่น")
                        for col, key in [("bedtime_screen_time_minutes", "f_screen"), ("doomscroller", "f_doom"),
                                         ("stress_score", "f_stress"), ("sleep_latency_minutes", "f_lat"),
                                         ("number_of_night_wakeups", "f_wake")]:
                            if got[col]:
                                ss[key] = got[col]; filled.append(key)
                        ss.fill_msg = (f"กรอกให้แล้ว {len(filled)} ช่อง — ตรวจดูด้านล่างก่อนกดบันทึก"
                                       + (f" ({got['note']})" if got["note"] else ""))
                    except LLMUnavailable as e:
                        ss.fill_msg = f"⚠️ {e}"
                    st.rerun()
            if llm is None:
                st.caption("ต้องใส่ GEMINI_API_KEY ก่อนถึงจะใช้ได้ (ดูวิธีใน README)")
            if ss.get("fill_msg"):
                st.caption(ss.fill_msg)

        st.markdown('<div class="step"><span>1</span>เวลานอน</div>', unsafe_allow_html=True)
        d = st.date_input("วันที่ (เช้าที่ตื่น)", date.today(), max_value=date.today(), format="DD/MM/YYYY")
        a, b = st.columns(2)
        bed = a.time_input("เข้านอน", step=900, key="f_bed")
        wake = b.time_input("ตื่น", step=900, key="f_wake_t")
        hours_now = sleep_duration(bed, wake)
        kk, ll = verdict(hours_now, lo, hi)
        st.markdown(f'<div class="preview"><span class="muted">คืนนี้นอนไป</span> '
                    f'<b style="font-size:1.3rem">{hours_now:.1f} ชม.</b> &nbsp;<span class="pill {kk}">{ll}</span></div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="step"><span>2</span>ก่อนนอน</div>', unsafe_allow_html=True)
        ans = {}
        ans["bedtime_screen_time_minutes"] = st.segmented_control(
            CHOICES["bedtime_screen_time_minutes"]["label"], list(CHOICES["bedtime_screen_time_minutes"]["options"]), key="f_screen")
        ans["doomscroller"] = st.segmented_control(YESNO["doomscroller"], ["ใช่", "ไม่ใช่"], key="f_doom")
        ans["stress_score"] = st.segmented_control(
            CHOICES["stress_score"]["label"], list(CHOICES["stress_score"]["options"]), key="f_stress")

        st.markdown('<div class="step"><span>3</span>ระหว่างคืน</div>', unsafe_allow_html=True)
        ans["sleep_latency_minutes"] = st.segmented_control(
            CHOICES["sleep_latency_minutes"]["label"], list(CHOICES["sleep_latency_minutes"]["options"]), key="f_lat")
        ans["number_of_night_wakeups"] = st.segmented_control(
            CHOICES["number_of_night_wakeups"]["label"], list(CHOICES["number_of_night_wakeups"]["options"]), key="f_wake")
        answered = sum(v is not None for v in ans.values())
        st.caption(f"ตอบแล้ว {answered}/5 ข้อ · ข้อไหนไม่แน่ใจเว้นไว้ได้ ระบบจะใช้ค่ากลางแทน — ดีกว่าเดาแล้วตอบผิด")
        if any(e["date"] == d for e in ss.entries):
            st.caption(f"มีบันทึกของวันที่ {d:%d/%m} อยู่แล้ว — บันทึกใหม่จะแทนที่ของเดิม")

        if st.button("บันทึกคืนนี้", type="primary", width="stretch"):
            entry = {"date": d, "bed": bed, "wake": wake, "hours": hours_now}
            for col, q in CHOICES.items():
                entry[col] = q["options"].get(ans[col])
            entry["doomscroller"] = {"ใช่": "Yes", "ไม่ใช่": "No"}.get(ans["doomscroller"])
            problems = check_input(bed, hours_now)
            if problems:
                ss.pending = (entry, problems)
            else:
                save(entry)
                st.rerun()
        if ss.pending:
            entry, problems = ss.pending
            st.warning("ตรวจสอบก่อนบันทึก:\n\n- " + "\n- ".join(problems))
            p1, p2 = st.columns(2)
            if p1.button("ถูกต้อง บันทึกเลย", width="stretch"):
                save(entry)
                st.rerun()
            if p2.button("กลับไปแก้", width="stretch"):
                ss.pending = None
                st.rerun()
        if ss.get("just_saved"):
            st.success(f"บันทึกคืนวันที่ {th_date(ss.just_saved)} แล้ว ✓")
            ss.just_saved = None

    with right:
        st.markdown('<div class="h-sec" style="margin-top:0">7 คืนล่าสุด</div>', unsafe_allow_html=True)
        rows = ""
        for _, r in df_all.tail(7).iloc[::-1].iterrows():
            kc, _l = verdict(r["Hours"], lo, hi)
            qk, qth = QUALITY_TH[r["Quality"]]
            rows += (f'<div class="night"><span class="d">{DAY_SHORT[r["Date"].weekday()]} {r["Date"].day}</span>'
                     f'<span class="bar"><i style="width:{min(r["Hours"] / 10, 1) * 100:.0f}%;background:{COLORS[kc]}"></i></span>'
                     f'<span class="h">{r["Hours"]:.1f} ชม.</span><span class="pill {qk}">{qth}</span></div>')
        st.markdown(rows or '<div class="muted">ยังไม่มีบันทึก</div>', unsafe_allow_html=True)
        if len(df_all):
            with st.expander(f"ดูประวัติทั้งหมด ({len(df_all)} คืน)"):
                show = pd.DataFrame({
                    "วันที่": df_all["Date"].dt.strftime("%d/%m/%Y"),
                    "เข้านอน": df_all["Bedtime"].map(lambda t: t.strftime("%H:%M")),
                    "ตื่น": df_all["Wake"].map(lambda t: t.strftime("%H:%M")),
                    "ชั่วโมง": df_all["Hours"], "คุณภาพ": df_all["Quality"].map(lambda q: QUALITY_TH[q][1]),
                    "โอกาสนอนแย่": df_all["P_Poor"] * 100}).iloc[::-1]
                st.dataframe(show, hide_index=True, width="stretch", height=380, column_config={
                    "ชั่วโมง": st.column_config.NumberColumn(format="%.1f"),
                    "โอกาสนอนแย่": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})
        with st.container(border=True):
            st.markdown('<div class="card-title" style="margin:0">ตั้งค่า</div>', unsafe_allow_html=True)
            new_age = st.selectbox("ช่วงอายุ (ใช้กำหนดเป้าหมายชั่วโมงนอน)", list(AGE_GROUPS),
                                   index=list(AGE_GROUPS).index(ss.age_group))
            if new_age != ss.age_group:
                ss.age_group = new_age
                st.rerun()
            if is_demo and st.button("ล้างข้อมูลตัวอย่าง แล้วเริ่มบันทึกของจริง", width="stretch"):
                ss.entries = [e for e in ss.entries if not e.get("sample")]
                ss.chat = []
                st.rerun()

# =========================================================
# วิเคราะห์
# =========================================================
with tabs[2]:
    if len(df_all) < 2:
        st.info("ต้องมีข้อมูลอย่างน้อย 2 คืน")
    else:
        h1, h2 = st.columns([3, 1])
        h1.markdown('<div class="h-sec" style="margin-top:0">ภาพรวมเชิงลึก</div>', unsafe_allow_html=True)
        with h2:
            period3, n3 = range_picker("analytics_range")
        stats3, df3 = calculate_statistics(df_all.tail(n3), lo)

        t1, t2, t3, t4 = st.columns(4)
        t1.markdown(tile("Σ", f"{stats3['short_nights']}/{stats3['nights']}", f"คืนที่นอนไม่ถึง {lo:.0f} ชม.", "a"), unsafe_allow_html=True)
        t2.markdown(tile("σ", hrs(stats3["std"]), "ความแกว่งของชั่วโมงนอน (SD)"), unsafe_allow_html=True)
        t3.markdown(tile("●", f"{stats3['good_share']:.0%}", "คืนที่คุณภาพดี (โมเดล)", "g"), unsafe_allow_html=True)
        t4.markdown(tile("●", f"{stats3['poor_share']:.0%}", "คืนที่คุณภาพแย่ (โมเดล)", "r"), unsafe_allow_html=True)

        g1, g2 = st.columns([1.5, 1], gap="medium")
        with g1, st.container(border=True):
            st.markdown('<div class="card-title">ชั่วโมงนอนเทียบเป้าหมาย</div>', unsafe_allow_html=True)
            f1 = go.Figure()
            f1.add_hrect(y0=lo, y1=hi, fillcolor="rgba(22,199,132,.08)", line_width=0)
            f1.add_trace(go.Scatter(x=df3["Date"], y=df3["Hours"], mode="lines", line=dict(color="#8b7cf6", width=3, shape="spline"),
                                    fill="tozeroy", fillcolor="rgba(139,124,246,.12)",
                                    hovertemplate="%{x|%d/%m} · <b>%{y:.1f} ชม.</b><extra></extra>"))
            f1.add_trace(go.Scatter(x=df3["Date"], y=df3["MA7"], mode="lines", line=dict(color="#f4f5fb", width=1.2, dash="dot"),
                                    hovertemplate="เฉลี่ย 7 คืน %{y:.1f} ชม.<extra></extra>"))
            f1.update_layout(height=300, **CHART, hovermode="x unified",
                             yaxis=dict(range=[max(0, df3["Hours"].min() - 1.5), max(10, df3["Hours"].max() + .5)],
                                        gridcolor="#1a1e31", ticksuffix=" ชม.", zeroline=False))
            st.plotly_chart(f1, width="stretch", config={"displayModeBar": False})
            st.caption(f"เส้นม่วง = ชั่วโมงนอน · เส้นประ = เฉลี่ย 7 คืน · แถบเขียว = เป้าหมาย {lo:.0f}–{hi:.0f} ชม.")
        with g2, st.container(border=True):
            st.markdown('<div class="card-title">นอนเฉลี่ยตามวันในสัปดาห์</div>', unsafe_allow_html=True)
            wd = weekday_average(df3).dropna()
            f2 = go.Figure(go.Bar(y=wd.index, x=wd.values, orientation="h", text=[f"{v:.1f}" for v in wd.values],
                                  textposition="outside", cliponaxis=False,
                                  marker=dict(color=[COLORS[verdict(v, lo, hi)[0]] for v in wd.values], cornerradius=6),
                                  hovertemplate="%{y} · %{x:.1f} ชม.<extra></extra>"))
            f2.add_vline(x=lo, line_dash="dot", line_color="#8f93ab")
            f2.update_layout(height=300, **{**CHART, "xaxis": dict(showgrid=False, visible=False, range=[0, max(10, wd.max() + 1)])},
                             yaxis=dict(autorange="reversed"))
            st.plotly_chart(f2, width="stretch", config={"displayModeBar": False})
            if len(wd):
                st.caption(f"นอนน้อยสุดคืนก่อนวัน{wd.idxmin()} ({wd.min():.1f} ชม.)")

        st.markdown('<div class="h-sec">สิ่งที่โมเดลพบ</div>', unsafe_allow_html=True)
        cc = cause_counts(df3)
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if i < len(cc):
                name, cnt = cc.index[i], cc.iloc[i]
                col.markdown(f"""<div class="card"><div class="card-title">อันดับ {i + 1}</div>
                    <div style="font-size:1.1rem;font-weight:700">{name}</div>
                    <div class="muted">พบใน {cnt} จาก {len(df3)} คืน</div>
                    <div class="night" style="background:none;padding:10px 0 0;margin:0"><span class="bar">
                    <i style="width:{cnt / len(df3) * 100:.0f}%;background:#8b7cf6"></i></span></div></div>""",
                             unsafe_allow_html=True)
        st.caption(f"โมเดล {meta['model']} · macro F1 = {meta['cv_f1_macro']} · "
                   "สาเหตุคำนวณจากการลองปรับทีละปัจจัยแล้วดูว่าโอกาสนอนแย่ลดลงเท่าไร")

# =========================================================
# ถาม AI — หน้าแชท
# =========================================================
with tabs[3]:
    if len(df_all) < 2:
        st.info("ต้องมีข้อมูลอย่างน้อย 2 คืน")
    else:
        h1, h2 = st.columns([3, 1])
        badge = ('<span class="chip"><span class="dot live"></span>Gemini เชื่อมต่อแล้ว</span>' if llm
                 else '<span class="chip"><span class="dot demo"></span>โหมดออฟไลน์ · ตอบจากกฎ</span>')
        h1.markdown(f'<div class="h-sec" style="margin-top:0">คุยกับผู้ช่วยการนอน &nbsp;{badge}</div>', unsafe_allow_html=True)
        with h2:
            period4, n4 = range_picker("chat_range")
        stats4, df4 = calculate_statistics(df_all.tail(n4), lo)

        context = build_context(period4, stats4, df4, (lo, hi))

        def answer(q):
            ss.chat.append(("user", q))
            ss.ask = q                      # คำตอบจะถูกสร้างตอน render ถัดไป (เพื่อให้ stream ทีละคำได้)

        chat_box = st.container(height=470, border=True)
        with chat_box:
            with st.chat_message("assistant", avatar="🌙"):
                st.markdown(f"สวัสดีครับ ผมดูข้อมูล **{stats4['nights']} คืนล่าสุด** ของคุณแล้ว — "
                            f"นอนเฉลี่ย **{stats4['mean']:.1f} ชม.** และมีหนี้การนอน **{stats4['sleep_debt']:.1f} ชม.** "
                            "อยากรู้อะไรเพิ่ม ถามได้เลย หรือกดคำถามด้านล่าง")
            for role, text in ss.chat:
                with st.chat_message(role, avatar="🌙" if role == "assistant" else "🙂"):
                    st.markdown(text, unsafe_allow_html=True)
            if ss.ask:
                q, ss.ask = ss.ask, None
                with st.chat_message("assistant", avatar="🌙"):
                    reply = None
                    if llm is not None:
                        try:
                            reply = st.write_stream(chat_stream(llm, ss.chat[:-1], q, context))
                        except LLMUnavailable as e:
                            st.caption(f"⚠️ {e} — ตอบจากกฎแทน")
                    if not reply:
                        reply = ask_sleep_ai(q, period4, stats4, df4, (lo, hi))
                        st.markdown(reply, unsafe_allow_html=True)
                ss.chat.append(("assistant", reply))

        chips = ["ช่วงนี้นอนพอไหม", "แนวโน้มสัปดาห์หน้า", "ทำไมนอนไม่ค่อยดี", "ควรปรับอะไรก่อน"]
        cc1, cc2, cc3, cc4, cc5 = st.columns([1, 1, 1, 1, .6])
        for col, q in zip([cc1, cc2, cc3, cc4], chips):
            if col.button(q, width="stretch", key=f"chip_{q}"):
                answer(q)
                st.rerun()
        if ss.chat and cc5.button("ล้างแชท", width="stretch"):
            ss.chat = []
            st.rerun()
        if q := st.chat_input("พิมพ์คำถามเกี่ยวกับการนอนของคุณ..."):
            answer(q)
            st.rerun()
        with st.expander("ดูข้อมูลสรุปที่ส่งให้ AI"):
            st.code(context, language=None)
