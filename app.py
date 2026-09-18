import calendar
import datetime as dt
import urllib.parse

import holidays
import pandas as pd
import streamlit as st

SHEET_ID = "1-4Z_h-mzrsZ-8e8lWsEn4EfofxZyF5PFcV2Rl9wiL9I"
SHEET_MAIN = "앱데이터"
SHEET_MEMO = "수기일정"   # 없으면 자동으로 무시됩니다

st.set_page_config(page_title="오더 일정", page_icon="📅", layout="centered")

st.markdown("""
<style>
  .block-container {padding-top: 3.2rem !important; padding-bottom: 4rem; max-width: 780px;}
  div[data-testid="column"] {padding: 0 1px !important;}
  div[data-testid="column"] .stButton > button {
      width: 100%; padding: 2px 0; min-height: 44px;
      font-size: 12px; line-height: 1.2; white-space: pre-line;
  }
  .dow {text-align:center; font-size:11px; padding-bottom:2px;}
  .dayhead {font-size:14px; font-weight:700; margin:14px 0 6px;}
  .ev {border-radius:7px; padding:6px 10px; margin-bottom:5px; font-size:13px;
       border:1px solid; line-height:1.35;}
  .ev .sub {font-size:11.5px; opacity:.85; margin-top:2px;}
  .ev a {color:inherit; text-decoration:underline;}
  .fill.c-blue  {background:#3b82f6; border-color:#3b82f6; color:#fff;}
  .fill.c-green {background:#22c55e; border-color:#22c55e; color:#fff;}
  .open.c-blue  {background:#fff; border-color:#c7ddfb; color:#1e40af;}
  .open.c-green {background:#fff; border-color:#c3ecd2; color:#15803d;}
  .open.c-peach {background:#fff; border-color:#fbd9b4; color:#9a4a10;}
  .open.c-gray  {background:#fff; border-color:#ddd; color:#444;}
  .fill.c-peach {background:#fdba74; border-color:#fdba74; color:#7c2d12;}
  .fill.c-gray  {background:#efefef; border-color:#e2e2e2; color:#333;}
  .dot {font-size:10px; margin-right:5px;}
  .empty {color:#bbb; font-size:12px; padding:2px 0 6px;}
</style>
""", unsafe_allow_html=True)

EXTRA_HOLIDAYS = {
    "2025-01-27": "임시공휴일",
    "2025-06-03": "대통령선거",
    "2026-06-03": "지방선거",
}


@st.cache_data(ttl=86400)
def build_holidays():
    try:
        kr = holidays.SouthKorea(years=range(2024, 2031), language="ko")
    except TypeError:
        kr = holidays.SouthKorea(years=range(2024, 2031))
    out = {d.strftime("%Y-%m-%d"): str(n) for d, n in kr.items()}
    out.update(EXTRA_HOLIDAYS)
    return out


HOLIDAYS = build_holidays()


def day_color(day):
    if day.strftime("%Y-%m-%d") in HOLIDAYS or day.weekday() == 6:
        return "#d33"
    if day.weekday() == 5:
        return "#2a6fd6"
    return "#222"


def csv_url(name):
    return (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(name)}")


@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(csv_url(SHEET_MAIN), dtype=str).fillna("")
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df["시공예정일"] = pd.to_datetime(df.get("시공예정일", ""), errors="coerce")
    df = df.dropna(subset=["날짜"]).copy()
    df["일자"] = df["날짜"].dt.date
    return df.sort_values(["일자", "구분"]).reset_index(drop=True)


@st.cache_data(ttl=300)
def load_memo():
    cols = ["날짜", "시간", "내용"]
    empty = pd.DataFrame(columns=cols + ["일자"])
    try:
        m = pd.read_csv(csv_url(SHEET_MEMO), dtype=str).fillna("")
    except Exception:
        return empty
    if not set(cols).issubset(m.columns) or "원본" in m.columns:
        return empty
    m["날짜"] = pd.to_datetime(m["날짜"], errors="coerce")
    m = m.dropna(subset=["날짜"]).copy()
    m["일자"] = m["날짜"].dt.date
    return m[cols + ["일자"]]


try:
    df = load_data()
except Exception as e:
    st.error("구글 시트를 읽을 수 없습니다. 시트 ID와 공유 설정을 확인하세요.")
    st.caption(str(e))
    st.stop()

memo = load_memo()
today = dt.date.today()
if "sel" not in st.session_state:
    st.session_state.sel = today


def esc(s):
    return str(s).replace("<", "&lt;").replace(">", "&gt;")


def event_html(r):
    if r.구분 == "실측":
        cls, fill = "c-peach", "open"
        plan = ""
        if pd.notna(r.시공예정일):
            plan = f"{r.시공예정일.month}월 {r.시공예정일.day}일"
        parts = [r.시공처 or r.가공처, r.시간, plan, r.파트너사]
    else:
        cls = "c-blue" if r.가공처 == "제이에스윈" else "c-green"
        fill = "fill" if r.발주 == "O" else "open"
        parts = [r.시공처, r.가공처, r.파트너사]
    title = " / ".join(esc(x) for x in parts if x)
    dot = "<span class='dot'>●</span>" if fill == "open" else ""
    addr = esc(r.현장주소)
    link = (f"<a href='https://map.naver.com/p/search/"
            f"{urllib.parse.quote(str(r.현장주소))}' target='_blank'>{addr}</a>") if addr else ""
    who = f"<div class='sub'>{esc(r.담당자)}</div>" if r.담당자 else ""
    return (f"<div class='ev {fill} {cls}'>{dot}<b>{title}</b>"
            f"<div class='sub'>{link}</div>{who}</div>")


def memo_html(r):
    txt = " ".join(x for x in [str(r.시간), str(r.내용)] if x)
    return f"<div class='ev fill c-gray'><b>{esc(txt)}</b></div>"


def render_day(day, show_head=True):
    dd = df[df["일자"] == day]
    mm = memo[memo["일자"] == day] if len(memo) else memo
    if show_head:
        hol = HOLIDAYS.get(day.strftime("%Y-%m-%d"), "")
        mark = " ◀ 오늘" if day == today else ""
        extra = f" <span style='color:#d33;font-size:12px'>{hol}</span>" if hol else ""
        st.markdown(
            f"<div class='dayhead' style='color:{day_color(day)}'>"
            f"{day.month}/{day.day} ({'일월화수목금토'[(day.weekday() + 1) % 7]}){extra}"
            f"<span style='color:#888;font-weight:400;font-size:12px'>{mark}</span></div>",
            unsafe_allow_html=True)
    html = "".join(memo_html(r) for r in mm.itertuples())
    html += "".join(event_html(r) for r in dd.itertuples())
    st.markdown(html if html else "<div class='empty'>일정 없음</div>",
                unsafe_allow_html=True)


# ── 상단 요약
upcoming = df[(df["구분"] == "시공") & (df["발주"] != "O")
              & (df["일자"] >= today) & (df["일자"] <= today + dt.timedelta(days=7))]
c1, c2 = st.columns(2)
c1.metric("오늘 일정", f"{len(df[df['일자'] == today])}건")
c2.metric("7일 내 발주 미완", f"{len(upcoming)}건")
if len(upcoming):
    with st.expander(f"발주해야 할 {len(upcoming)}건 보기"):
        for r in upcoming.itertuples():
            st.markdown(
                f"<div class='ev open {'c-blue' if r.가공처 == '제이에스윈' else 'c-green'}'>"
                f"<span class='dot'>●</span><b>{r.일자.month}/{r.일자.day} · "
                f"{esc(' / '.join(x for x in [r.시공처, r.가공처, r.파트너사] if x))}</b>"
                f"<div class='sub'>{esc(r.현장주소)}</div></div>",
                unsafe_allow_html=True)

view = st.radio("보기", ["주간", "월간", "검색"], horizontal=True,
                label_visibility="collapsed")

# ── 주간
if view == "주간":
    sel = st.session_state.sel
    start = sel - dt.timedelta(days=(sel.weekday() + 1) % 7)
    end = start + dt.timedelta(days=6)
    a, b, c = st.columns([1, 3, 1])
    if a.button("◀", use_container_width=True):
        st.session_state.sel = sel - dt.timedelta(days=7)
        st.rerun()
    if c.button("▶", use_container_width=True):
        st.session_state.sel = sel + dt.timedelta(days=7)
        st.rerun()
    b.markdown(f"<h4 style='text-align:center;margin:0'>{start.month}/{start.day} "
               f"~ {end.month}/{end.day}</h4>", unsafe_allow_html=True)
    if st.button("이번 주로", use_container_width=True):
        st.session_state.sel = today
        st.rerun()
    st.divider()
    for i in range(7):
        render_day(start + dt.timedelta(days=i))

# ── 월간
elif view == "월간":
    sel = st.session_state.sel
    y, m = sel.year, sel.month
    a, b, c = st.columns([1, 3, 1])
    if a.button("◀", use_container_width=True):
        pm = (m - 2) % 12 + 1
        py = y - 1 if m == 1 else y
        st.session_state.sel = dt.date(py, pm, 1)
        st.rerun()
    if c.button("▶", use_container_width=True):
        nm = m % 12 + 1
        ny = y + 1 if m == 12 else y
        st.session_state.sel = dt.date(ny, nm, 1)
        st.rerun()
    b.markdown(f"<h4 style='text-align:center;margin:0'>{y}년 {m}월</h4>",
               unsafe_allow_html=True)

    mdf = df[(df["날짜"].dt.year == y) & (df["날짜"].dt.month == m)]
    cols = st.columns(7)
    for col, d, c_ in zip(cols, "일월화수목금토",
                          ["#d33"] + ["#333"] * 5 + ["#2a6fd6"]):
        col.markdown(f"<div class='dow' style='color:{c_}'>{d}</div>",
                     unsafe_allow_html=True)

    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(y, m):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            if day.month != m:
                col.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            dd = mdf[mdf["일자"] == day]
            n_blue = len(dd[(dd["구분"] == "시공") & (dd["가공처"] == "제이에스윈")])
            n_green = len(dd[(dd["구분"] == "시공") & (dd["가공처"] != "제이에스윈")])
            n_peach = len(dd[dd["구분"] == "실측"])
            bits = []
            if n_blue:
                bits.append(f":blue[●{n_blue}]")
            if n_green:
                bits.append(f":green[●{n_green}]")
            if n_peach:
                bits.append(f":orange[●{n_peach}]")
            todo = len(dd[(dd["구분"] == "시공") & (dd["발주"] != "O")])
            mark = "❗" if todo else ""
            is_sel = day == st.session_state.sel
            col_hex = day_color(day)
            if is_sel:
                num = str(day.day)
            elif col_hex == "#d33":
                num = f":red[{day.day}]"
            elif col_hex == "#2a6fd6":
                num = f":blue[{day.day}]"
            else:
                num = str(day.day)
            if col.button(f"{num}{mark}\n{' '.join(bits)}", key=f"d{day}",
                          type="primary" if is_sel else "secondary"):
                st.session_state.sel = day
                st.rerun()
    st.divider()
    render_day(st.session_state.sel)

# ── 검색
else:
    q = st.text_input("주소·파트너사·담당자·가공처 검색", placeholder="예: 목동  /  헤나  /  한길")
    if q:
        mask = df.apply(lambda r: q in " ".join(
            [str(r["현장주소"]), str(r["파트너사"]), str(r["담당자"]),
             str(r["가공처"]), str(r["시공처"])]), axis=1)
        hit = df[mask]
        st.caption(f"{len(hit)}건")
        for day, g in hit.groupby("일자"):
            st.markdown(f"<div class='dayhead' style='color:{day_color(day)}'>"
                        f"{day.year}. {day.month}/{day.day}</div>", unsafe_allow_html=True)
            st.markdown("".join(event_html(r) for r in g.itertuples()),
                        unsafe_allow_html=True)

st.divider()
st.caption(f"총 {len(df):,}건 · 5분마다 갱신")
if st.button("지금 새로고침"):
    st.cache_data.clear()
    st.rerun()
