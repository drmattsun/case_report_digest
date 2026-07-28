"""
毎日の最新ケースレポート・ダイジェスト (Streamlitダッシュボード) — 完全無料版

要約・翻訳は行わず、PubMedのタイトル・抄録(英語)をそのまま表示します。
PubMed(NCBI E-utilities)は無料APIのため、本アプリの利用に費用は一切かかりません。

起動方法:
    streamlit run app.py

事前に環境変数を設定してください(任意):
    NCBI_API_KEY  ... 任意(PubMedのレート制限緩和用。なくても動作します)
"""

import datetime

import streamlit as st

from pubmed_client import get_latest_case_reports

st.set_page_config(page_title="ケースレポート・デイリーダイジェスト", page_icon="📋", layout="wide")

st.title("📋 毎日のケースレポート・ダイジェスト")
st.caption("PubMed発表の最新ケースレポートを取得して一覧表示します(英語抄録・完全無料)。")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("設定")
    days = st.slider("何日以内に発表された論文を対象にするか", min_value=1, max_value=7, value=1)
    retmax = st.slider("最大取得件数", min_value=5, max_value=50, value=15, step=5)
    extra_term = st.text_input(
        "絞り込みキーワード(任意・PubMed検索構文)",
        placeholder='例: cardiology[MeSH Terms]',
        help="診療科などで絞り込みたい場合に入力してください。空欄なら医学全般が対象です。",
    )
    st.markdown("---")
    st.caption("このアプリはPubMedの無料APIのみを使用しており、費用は一切かかりません。")


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)  # 1日キャッシュ(毎日1回だけ取得する)
def load_digest(days: int, retmax: int, extra_term: str, cache_date: str):
    """cache_date(今日の日付文字列)が変わるとキャッシュが自動的に無効化される。"""
    return get_latest_case_reports(days=days, retmax=retmax, extra_term=extra_term or None)


col1, col2 = st.columns([1, 5])
with col1:
    manual_refresh = st.button("🔄 今すぐ更新", use_container_width=True)

if manual_refresh:
    load_digest.clear()

today_str = datetime.date.today().isoformat()

with st.spinner("PubMedから最新のケースレポートを取得しています…"):
    try:
        digest = load_digest(days, retmax, extra_term, today_str)
    except Exception as e:
        st.error(f"取得中にエラーが発生しました: {e}")
        st.stop()

st.markdown(f"**{today_str}時点 / 直近{days}日以内に発表された論文: {len(digest)}件**")
st.markdown("---")

if not digest:
    st.info("該当する新着ケースレポートが見つかりませんでした。日数や絞り込み条件を変更してみてください。")

for i, report in enumerate(digest, start=1):
    with st.container(border=True):
        st.subheader(f"{i}. {report.title}")
        st.caption(f"{report.journal} | 発行日: {report.pub_date} | 著者: {report.authors}")
        st.write(report.abstract)
        st.markdown(f"[PubMedで原文を見る ↗]({report.url})  ・  PMID: {report.pmid}")

st.markdown("---")
st.caption(
    "本ダッシュボードは情報提供のみを目的としており、診断・治療の判断は必ず一次資料と専門家の確認に基づいて行ってください。"
)
