import streamlit as st
# ページ設定（最初に呼び出す必要あり）
st.set_page_config(page_title="TEST", layout="centered")

# デバッグメッセージを UI に出力
st.write("🐞 test_login.py loaded")

# 追加: コンソール向けデバッグ
import logging
logging.basicConfig(level=logging.DEBUG)
print('🐞 console: test_login.py loaded')

import os, sys
from pathlib import Path  # 追加: ファイル位置からルートディレクトリを計算
# Ensure project root is in sys.path for module imports
# 修正: __file__ の親ディレクトリをルートとして使用
root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
st.write(f"DEBUG: sys.path={sys.path}")

# 追加: sys.pathデバッグ出力(コンソール)
print(f"🐞 console: sys.path={sys.path}")

# Remove script filename entries to avoid import confusion
sys.path = [p for p in sys.path if not p.endswith('test_login.py')]
st.write(f"DEBUG: cleaned sys.path={sys.path}")
print(f"🐞 console: cleaned sys.path={sys.path}")

# ログイン画面の関数をインポートして例外があれば表示
# 既存のtry/exceptの前に追加: インポート前のデバッグ
print('🐞 console: before importing show_login_screen')
try:
    from utils.ui_utils import show_login_screen
    st.write("🐞 Imported show_login_screen")
    # 既存のtryブロック内直後に追加: インポート成功時のデバッグ
    # ここでは既に st.write しているが、コンソールにも出力
    print('🐞 console: imported show_login_screen successfully')
except Exception as e:
    st.write(f"🐞 Import error: {e}")
    # except ブロック内に追加: インポート失敗時のデバッグ
    print(f"🐞 console: import error: {e}")
    show_login_screen = None

# 関数が正しくインポートできていれば呼び出し
# 既存のif show_login_screenの直前に追加
print(f"🐞 console: show_login_screen is {'available' if show_login_screen else 'unavailable'}")
if show_login_screen:
    st.write("🐞 Calling show_login_screen()")
    # 既存の if show_login_screen ブロック内先頭に追加
    print('🐞 console: calling show_login_screen()')
    try:
        show_login_screen()
        st.write("🐞 show_login_screen() returned")
    except Exception as e:
        st.write(f"🐞 show_login_runtime_error: {e}")
        # さらに except 内に追加: ランタイムエラー
        print(f"🐞 console: show_login_runtime_error: {e}")
else:
    st.write("🐞 show_login_screen unavailable")
                    
st.stop()