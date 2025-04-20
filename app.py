import streamlit as st
from utils.ui_utils import show_header, show_success_message, show_error_message, init_session_state
from utils.db_utils import register_user, login_user
import datetime
import os
import sys

# セッション状態の初期化
init_session_state()

# ページ設定
st.set_page_config(
    page_title="買い物アプリ",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ヘッダー表示
show_header("買い物アプリ 🛒")

# タブの作成
tab1, tab2 = st.tabs(["ログイン", "新規登録"])

with tab1:
    st.subheader("ログイン")
    
    with st.form("login_form", clear_on_submit=True):
        email = st.text_input("メールアドレス", placeholder="example@mail.com")
        password = st.text_input("パスワード", type="password")
        submit_button = st.form_submit_button("ログイン")

        if submit_button:
            if not email or not password:
                show_error_message("メールアドレスとパスワードを入力してください")
            else:
                user_data = login_user(email, password)
                if user_data:
                    # ログイン成功
                    st.session_state['user_id'] = user_data['user_id']
                    st.session_state['user_token'] = user_data['token']
                    show_success_message(f"{user_data['name']}さん、ようこそ！")
                    
                    # ホームページへリダイレクト
                    st.switch_page("pages/01_ホーム.py")
                else:
                    # ログイン失敗
                    show_error_message("メールアドレスまたはパスワードが正しくありません")

with tab2:
    st.subheader("新規登録")
    
    with st.form("register_form", clear_on_submit=True):
        new_name = st.text_input("お名前", placeholder="買い物太郎")
        new_email = st.text_input("メールアドレス", placeholder="example@mail.com")
        new_password = st.text_input("パスワード", type="password")
        new_password_confirm = st.text_input("パスワード（確認）", type="password")
        submit_button = st.form_submit_button("登録する")
        
        if submit_button:
            if not new_name or not new_email or not new_password:
                show_error_message("すべての項目を入力してください")
            elif new_password != new_password_confirm:
                show_error_message("パスワードが一致しません")
            else:
                new_user = register_user(new_email, new_password, new_name)
                if new_user:
                    # 登録成功
                    show_success_message("登録が完了しました！ログインしてください")
                    # ログインタブに切り替え
                    st.rerun()
                else:
                    # 登録失敗
                    show_error_message("このメールアドレスは既に登録されています")

# フッター情報
st.divider()
st.caption("© 2025 買い物アプリ")
today = datetime.date.today()
st.caption(f"今日の日付: {today.strftime('%Y年%m月%d日')}")