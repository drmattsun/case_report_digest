"""
毎日の最新ケースレポート・ダイジェスト (Streamlitダッシュボード)

要約・翻訳は行わず、PubMedのタイトル・抄録(英語)をそのまま表示します。
PubMed(NCBI E-utilities)は無料APIのため、閲覧自体に費用は一切かかりません。

「お気に入り保存」機能はGoogleアカウントでログインした人だけが使えます。
ログインしなくても、最新ケースレポートの閲覧は誰でも可能です。

起動方法:
    streamlit run app.py

Googleログインを使うには .streamlit/secrets.toml の設定が必要です。
詳しくは README.md を参照してください。
"""

import datetime

import streamlit as st

from pubmed_client import SPECIALTY_CATEGORIES, get_latest_case_reports
from favorites_store import add_favorite, load_favorites, remove_favorite

st.set_page_config(page_title="ケースレポート・デイリーダイジェスト", page_icon="📋", layout="wide")

st.title("📋 毎日のケースレポート・ダイジェスト")
st.caption("PubMed発表の最新ケースレポート(ヒト症例)を取得して一覧表示します(英語抄録・完全無料)。")

# --- ログイン状態の確認 ---
# secrets.toml で [auth] が設定されていない場合、st.user へのアクセスは例外になるため
# try/exceptで安全に判定する(未設定でもアプリ自体は動作させたいため)。
try:
    is_logged_in = bool(st.user.is_logged_in)
    user_email = st.user.email if is_logged_in else None
    user_name = st.user.get("name", user_email) if is_logged_in else None
    auth_configured = True
except Exception:
    is_logged_in = False
    user_email = None
    user_name = None
    auth_configured = False

# --- サイドバー: ログイン/ログアウト ---
with st.sidebar:
    st.header("アカウント")
    if not auth_configured:
        st.caption("ログイン機能は現在未設定です(お気に入りなしでご利用いただけます)。")
    elif is_logged_in:
        st.success(f"ログイン中: {user_name}")
        st.button("ログアウト", on_click=st.logout, use_container_width=True)
    else:
        st.info("ログインすると、お気に入り保存機能が使えます。")
        st.button("Googleでログイン", on_click=st.login, use_container_width=True)

    st.markdown("---")
    st.header("設定")
    days = st.slider("何日以内に発表された論文を対象にするか", min_value=1, max_value=7, value=1)
    retmax = st.slider("最大取得件数", min_value=5, max_value=50, value=15, step=5)

    st.markdown("---")
    st.subheader("診療科で絞り込み")
    st.caption("チェックを入れなければ、医学全般(全科)が対象になります。")
    selected_categories = []
    category_names = list(SPECIALTY_CATEGORIES.keys())
    col_a, col_b = st.columns(2)
    for i, name in enumerate(category_names):
        target_col = col_a if i % 2 == 0 else col_b
        if target_col.checkbox(name, value=False, key=f"cat_{name}"):
            selected_categories.append(name)

    st.markdown("---")
    extra_term = st.text_input(
        "追加の検索キーワード(任意・PubMed検索構文)",
        placeholder='例: rare disease[Title]',
    )
    st.caption("動物実験などは自動的に除外し、ヒトの症例のみを対象にしています。")


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)  # 1日キャッシュ(毎日1回だけ取得する)
def load_digest(days: int, retmax: int, extra_term: str, categories: tuple, cache_date: str):
    """cache_date(今日の日付文字列)が変わるとキャッシュが自動的に無効化される。"""
    return get_latest_case_reports(
        days=days,
        retmax=retmax,
        extra_term=extra_term or None,
        humans_only=True,
        categories=list(categories) if categories else None,
    )


col1, col2 = st.columns([1, 5])
with col1:
    manual_refresh = st.button("🔄 今すぐ更新", use_container_width=True)

if manual_refresh:
    load_digest.clear()

today_str = datetime.date.today().isoformat()

if is_logged_in:
    tab_latest, tab_favorites = st.tabs(["📰 最新ケースレポート", "⭐ お気に入り"])
else:
    (tab_latest,) = st.tabs(["📰 最新ケースレポート"])
    tab_favorites = None

# --- 最新ケースレポート タブ ---
with tab_latest:
    with st.spinner("PubMedから最新のケースレポートを取得しています…"):
        try:
            digest = load_digest(days, retmax, extra_term, tuple(sorted(selected_categories)), today_str)
        except Exception as e:
            st.error(f"取得中にエラーが発生しました: {e}")
            st.stop()

    filter_note = f"(絞り込み: {'・'.join(selected_categories)})" if selected_categories else "(全科)"
    st.markdown(f"**{today_str}時点 / 直近{days}日以内 {filter_note} / 該当: {len(digest)}件**")

    if not is_logged_in and auth_configured:
        st.caption("💡 ログインすると、各論文を「お気に入り」に保存できるようになります。")

    st.markdown("---")

    if not digest:
        st.info("該当する新着ケースレポートが見つかりませんでした。日数や絞り込み条件を変更してみてください。")

    current_favorites = load_favorites(user_email) if is_logged_in else {}

    for i, report in enumerate(digest, start=1):
        with st.container(border=True):
            if is_logged_in:
                title_col, star_col = st.columns([8, 1])
            else:
                title_col = st.container()
                star_col = None

            with title_col:
                st.subheader(f"{i}. {report.title}")

            if is_logged_in and star_col is not None:
                with star_col:
                    already_saved = report.pmid in current_favorites
                    if already_saved:
                        if st.button("★ 保存済み", key=f"unsave_{report.pmid}", use_container_width=True):
                            remove_favorite(user_email, report.pmid)
                            st.rerun()
                    else:
                        if st.button("☆ 保存", key=f"save_{report.pmid}", use_container_width=True):
                            add_favorite(user_email, report)
                            st.rerun()

            st.caption(f"{report.journal} | 発行日: {report.pub_date} | 著者: {report.authors}")
            st.write(report.abstract)
            st.markdown(f"[PubMedで原文を見る ↗]({report.url})  ・  PMID: {report.pmid}")

# --- お気に入り タブ(ログイン時のみ表示) ---
if is_logged_in and tab_favorites is not None:
    with tab_favorites:
        favorites = load_favorites(user_email)
        st.markdown(f"**{user_name} さんの保存済み: {len(favorites)}件**")
        st.caption(
            "※ このアプリをStreamlit Community Cloud等の無料ホスティングで使っている場合、"
            "長時間アクセスがないとデータが消えることがあります。重要な論文はPubMedのリンクも"
            "別途保存しておくことをおすすめします。"
        )
        st.markdown("---")

        if not favorites:
            st.info("まだお気に入りが保存されていません。「最新ケースレポート」タブの ☆ 保存 ボタンから追加できます。")

        for pmid, data in favorites.items():
            with st.container(border=True):
                title_col, star_col = st.columns([8, 1])
                with title_col:
                    st.subheader(data["title"])
                with star_col:
                    if st.button("🗑 削除", key=f"remove_{pmid}", use_container_width=True):
                        remove_favorite(user_email, pmid)
                        st.rerun()

                st.caption(f"{data['journal']} | 発行日: {data['pub_date']} | 著者: {data['authors']}")
                st.write(data["abstract"])
                st.markdown(f"[PubMedで原文を見る ↗]({data['url']})  ・  PMID: {pmid}")

st.markdown("---")
st.caption(
    "本ダッシュボードは情報提供のみを目的としており、診断・治療の判断は必ず一次資料と専門家の確認に基づいて行ってください。"
)
