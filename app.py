import streamlit as st
# ページ設定：最初に呼び出す必要があります
st.set_page_config(
    page_title="買い物アプリ",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
# デバッグ用セッションクリアは削除しました
import sys
from pathlib import Path
# Ensure project root is in sys.path for module imports
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.ui_utils import init_session_state, show_login_screen
import datetime
import os

if st.sidebar.button("全セッションをクリア"):
    st.session_state.clear()
    st.rerun()

# セッション状態の初期化
init_session_state()

# 認証チェック: 未ログイン時はログイン画面を表示して停止

if not st.session_state.get('user_id'):
    show_login_screen()
    st.stop()

# ログイン済みの場合はホームページへリダイレクト
st.switch_page("pages/01_ホーム.py")

# フッターやその他UIは各ページで表示します

dark_bg = "#0e1117"

css = f"""
<style>
:root {{
    --primary-background-color:   {dark_bg};
    --secondary-background-color: {dark_bg};
}}
.stSpacer, div[style*="position: sticky"][style*="bottom"] {{
    background: {dark_bg} !important;
}}
html, body, .stApp {{
    background: {dark_bg} !important;
    min-height: 100vh; /* ページ全体をカバー */
}}
</style>
"""

st.markdown(css, unsafe_allow_html=True)

