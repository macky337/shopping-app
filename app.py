import streamlit as st
import os
import socket

def find_free_port(default_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', default_port)) != 0:
            return default_port
        for port in range(default_port+1, default_port+100):
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return default_port

port = find_free_port(int(os.environ.get("PORT", 8501)))

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

# 注意:
# Streamlitを「streamlit run app.py」で起動した場合、このファイル内でポートを自動選択しても反映されません。
# ポート競合を避けるには、コマンドラインで「streamlit run app.py --server.port 8505」などと指定してください。
# もしくは「python app.py」で起動すると自動ポート選択が有効になります。

# 注意:
# Streamlitの起動ログに「URL: http://0.0.0.0:8501」と表示されても、
# ブラウザでは「http://localhost:8501」または「http://127.0.0.1:8501」でアクセスしてください。

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

