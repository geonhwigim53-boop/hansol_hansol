import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="국내 주식 대시보드",
    page_icon="📈",
    layout="wide",
)

# 국내 주요 주식 10개 (야후파이낸스 티커: 종목코드.KS 또는 .KQ)
STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS",
    "현대차": "005380.KS",
    "POSCO홀딩스": "005490.KS",
    "카카오": "035720.KS",
    "NAVER": "035420.KS",
    "기아": "000270.KS",
    "셀트리온": "068270.KS",
}

PERIOD_OPTIONS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
}

st.title("📈 국내 주식 대시보드")
st.caption("yfinance 기반 국내 주요 주식 10종목 실시간 분석")

# 사이드바
st.sidebar.header("설정")
selected_names = st.sidebar.multiselect(
    "종목 선택",
    options=list(STOCKS.keys()),
    default=list(STOCKS.keys())[:5],
)
period_label = st.sidebar.selectbox("기간", list(PERIOD_OPTIONS.keys()), index=2)
period = PERIOD_OPTIONS[period_label]
chart_type = st.sidebar.radio("차트 유형", ["라인", "캔들스틱"])

if not selected_names:
    st.warning("왼쪽에서 종목을 1개 이상 선택하세요.")
    st.stop()

selected_tickers = {name: STOCKS[name] for name in selected_names}


@st.cache_data(ttl=300)
def fetch_stock_data(ticker: str, period: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    info = stock.fast_info
    return hist, info


# ── 요약 카드 ────────────────────────────────────────────────
st.subheader("종목 요약")
cols = st.columns(len(selected_names))

summary_rows = []
for col, (name, ticker) in zip(cols, selected_tickers.items()):
    hist, info = fetch_stock_data(ticker, period)
    if hist.empty:
        col.warning(f"{name}\n데이터 없음")
        continue

    current = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
    change = current - prev
    change_pct = (change / prev) * 100

    color = "🔴" if change < 0 else ("🟢" if change > 0 else "⚪")
    col.metric(
        label=f"{color} {name}",
        value=f"{current:,.0f}원",
        delta=f"{change:+,.0f} ({change_pct:+.2f}%)",
    )
    summary_rows.append(
        {
            "종목": name,
            "현재가": current,
            "전일대비": change,
            "등락률(%)": round(change_pct, 2),
            "거래량": hist["Volume"].iloc[-1],
            "52주 최고": hist["High"].max(),
            "52주 최저": hist["Low"].min(),
        }
    )

st.divider()

# ── 주가 차트 ────────────────────────────────────────────────
st.subheader(f"주가 차트 ({period_label})")

if chart_type == "라인":
    fig = go.Figure()
    for name, ticker in selected_tickers.items():
        hist, _ = fetch_stock_data(ticker, period)
        if not hist.empty:
            fig.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["Close"],
                    mode="lines",
                    name=name,
                    hovertemplate="%{x}<br>%{y:,.0f}원<extra></extra>",
                )
            )
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="종가 (원)",
        hovermode="x unified",
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # 캔들스틱 — 종목 하나씩
    candle_name = st.selectbox("캔들스틱 종목", list(selected_tickers.keys()))
    candle_ticker = selected_tickers[candle_name]
    hist, _ = fetch_stock_data(candle_ticker, period)
    if not hist.empty:
        fig = go.Figure(
            go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name=candle_name,
                increasing_line_color="red",
                decreasing_line_color="blue",
            )
        )
        fig.update_layout(
            title=f"{candle_name} 캔들스틱",
            xaxis_title="날짜",
            yaxis_title="가격 (원)",
            xaxis_rangeslider_visible=False,
            height=480,
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 거래량 차트 ────────────────────────────────────────────────
st.subheader("거래량 비교 (최근 30일 평균)")
vol_data = []
for name, ticker in selected_tickers.items():
    hist, _ = fetch_stock_data(ticker, period)
    if not hist.empty:
        avg_vol = hist["Volume"].tail(30).mean()
        vol_data.append({"종목": name, "평균거래량": avg_vol})

if vol_data:
    vol_df = pd.DataFrame(vol_data).sort_values("평균거래량", ascending=True)
    fig_vol = px.bar(
        vol_df,
        x="평균거래량",
        y="종목",
        orientation="h",
        color="평균거래량",
        color_continuous_scale="Blues",
        text_auto=".3s",
    )
    fig_vol.update_layout(height=350, coloraxis_showscale=False)
    st.plotly_chart(fig_vol, use_container_width=True)

st.divider()

# ── 수익률 비교 ────────────────────────────────────────────────
st.subheader(f"기간 수익률 비교 ({period_label})")
ret_data = []
for name, ticker in selected_tickers.items():
    hist, _ = fetch_stock_data(ticker, period)
    if not hist.empty and len(hist) > 1:
        ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
        ret_data.append({"종목": name, "수익률(%)": round(ret, 2)})

if ret_data:
    ret_df = pd.DataFrame(ret_data).sort_values("수익률(%)", ascending=True)
    colors = ["red" if v < 0 else "blue" for v in ret_df["수익률(%)"]]
    fig_ret = px.bar(
        ret_df,
        x="수익률(%)",
        y="종목",
        orientation="h",
        color="수익률(%)",
        color_continuous_scale=["#0055ff", "#cccccc", "#ff2222"],
        color_continuous_midpoint=0,
        text_auto=".2f",
    )
    fig_ret.update_layout(height=350, coloraxis_showscale=False)
    st.plotly_chart(fig_ret, use_container_width=True)

st.divider()

# ── 상세 데이터 테이블 ────────────────────────────────────────
st.subheader("종목 상세 데이터")
if summary_rows:
    df_summary = pd.DataFrame(summary_rows).set_index("종목")
    df_summary["현재가"] = df_summary["현재가"].map("{:,.0f}".format)
    df_summary["전일대비"] = df_summary["전일대비"].map("{:+,.0f}".format)
    df_summary["등락률(%)"] = df_summary["등락률(%)"].map("{:+.2f}%".format)
    df_summary["거래량"] = df_summary["거래량"].map("{:,.0f}".format)
    df_summary["52주 최고"] = df_summary["52주 최고"].map("{:,.0f}".format)
    df_summary["52주 최저"] = df_summary["52주 최저"].map("{:,.0f}".format)
    st.dataframe(df_summary, use_container_width=True)

st.caption(f"데이터 출처: Yahoo Finance (yfinance) | 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
