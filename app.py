import calendar
import datetime as dt
import urllib.parse

import pandas as pd
import streamlit as st

# ▼▼▼ 이 줄의 따옴표 안에 구글 시트 ID를 넣으세요 ▼▼▼
SHEET_ID = "1-4Z_h-mzrsZ-8e8lWsEn4EfofxZyF5PFcV2Rl9wiL9I"
# ▲▲▲ 예: SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890" ▲▲▲

SHEET_NAME = "앱데이터"

st.set_page_config(page_title="오더 일정", page_icon="📅", layout="centered")

st.markdown("""
<style>
  .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
  div[data-testid="column"] {padding: 0 1px !important;}
  div[data-testid="column"] .stButton > button {
      width: 100%; padding: 2px 0; min-height: 46px;
      font-size: 12px; line-height: 1.25; white-space: pre-line;
  }
  .dow {text-align:center; font-size:11px; color:#888; padding-bottom:2px;}
  .card {border:1px solid #e6e6e6; border-radius:10px; padding:10px 12px; margin-bottom:8px;}
  .tag {display:inline-block; font-size:11px; padding:1px 7px; border-radius:9px; margin-right:6px;}
  .t-si {background:#e7f0fb; color:#1f4e79;}
  .t-sc {background:#fdeaea; color:#9c2a2a;}
  .meta {font-size:12px; color:#666; margin-top:3px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(SHEET_NAME)}")
    df = pd.read_csv(url, dtype=str).fillna("")
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"]).copy()
    df["일자"] = df["날짜"].dt.date
    return df.sort_values(["일자", "구분"]).reset_index(drop=True)


try:
    df = load_data()
except Exception as e:
    st.error("구글 시트를 읽을 수 없습니다. 시트 ID와 공유 설정(링크가 있는 모든 사용자·뷰어)을 확인하세요.")
    st.caption(str(e))
    st.stop()

today = dt.date.today()
if "ym" not in st.session_state:
    st.session_state.ym = (today.year, today.month)
if "sel" not in st.session_state:
    st.session_state.sel = today


def shift_month(delta):
    y, m = st.session_state.ym
    m += delta
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    st.session_state.ym = (y, m)


c1, c2, c3 = st.columns([1, 3, 1])
c1.button("◀", use_container_width=True, on_click=shift_month, args=(-1,))
c3.button("▶", use_container_width=True, on_click=shift_month, args=(1,))
y, m = st.session_state.ym
c2.markdown(f"<h3 style='text-align:center;margin:0'>{y}년 {m}월</h3>", unsafe_allow_html=True)

with st.expander("필터", expanded=False):
    kinds = st.multiselect("구분", ["시공", "실측"], default=["시공", "실측"])
    ga_opts = sorted(x for x in df["가공처"].unique() if x)
    sg_opts = sorted(x for x in df["시공처"].unique() if x)
    ga = st.multiselect("가공처", ga_opts)
    sg = st.multiselect("시공처", sg_opts)
    only_no_order = st.checkbox("발주 안 된 건만", value=False)

f = df[df["구분"].isin(kinds)]
if ga:
    f = f[f["가공처"].isin(ga)]
if sg:
    f = f[f["시공처"].isin(sg)]
if only_no_order:
    f = f[f["발주"] != "O"]

month_df = f[(f["날짜"].dt.year == y) & (f["날짜"].dt.month == m)]
counts = month_df.groupby("일자").size().to_dict()

view = st.radio("보기", ["월간", "목록"], horizontal=True, label_visibility="collapsed")

if view == "월간":
    cols = st.columns(7)
    for col, d in zip(cols, ["일", "월", "화", "수", "목", "금", "토"]):
        col.markdown(f"<div class='dow'>{d}</div>", unsafe_allow_html=True)

    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(y, m):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            if day.month != m:
                col.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            n = counts.get(day, 0)
            label = f"{day.day}\n{'●' * min(n, 3) if n else ''}"
            if col.button(label, key=f"d{day}",
                          type="primary" if day == st.session_state.sel else "secondary"):
                st.session_state.sel = day
                st.rerun()

    st.divider()
    sel = st.session_state.sel
    day_df = month_df[month_df["일자"] == sel]
    st.markdown(f"**{sel.strftime('%m월 %d일')}** · {len(day_df)}건")
    rows = list(day_df.itertuples())
    if not rows:
        st.caption("해당 날짜에 일정이 없습니다.")
else:
    st.divider()
    rows = list(month_df.itertuples())

last_day = None
for r in rows:
    if view == "목록" and r.일자 != last_day:
        st.markdown(f"**{r.일자.strftime('%m/%d')}**")
        last_day = r.일자
    tag = "t-sc" if r.구분 == "실측" else "t-si"
    time_txt = f" {r.시간}" if r.시간 else ""
    order = "" if r.발주 == "O" else " · <b style='color:#c0392b'>발주 미완</b>"
    maker = " / ".join(x for x in [r.가공처, r.시공처] if x)
    addr = r.현장주소
    link = f"https://map.naver.com/p/search/{urllib.parse.quote(addr)}" if addr else ""
    st.markdown(f"""
    <div class='card'>
      <span class='tag {tag}'>{r.구분}{time_txt}</span><b>{r.거래처}</b>{order}
      <div class='meta'>{addr}</div>
      <div class='meta'>{maker}{' · ' if maker else ''}<a href='{link}' target='_blank'>지도</a></div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption(f"총 {len(df):,}건 · 5분마다 갱신")
if st.button("지금 새로고침"):
    st.cache_data.clear()
    st.rerun()
