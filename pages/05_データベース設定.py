import streamlit as st
import os
from utils.ui_utils import show_header, show_success_message, show_error_message
from utils.ui_utils import check_authentication, show_connection_indicator
from utils.db_utils import get_db_health_check
from dotenv import load_dotenv
from utils.ui_utils import patch_dark_background

# 認証チェック
if not check_authentication():
    st.stop()

# ページ設定
st.set_page_config(
    page_title="データベース設定 | 買い物アプリ",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

patch_dark_background()

# ヘッダー表示
show_header("データベース設定 🛢️")

# 環境変数の読み込み
load_dotenv()
db_url = os.getenv("DATABASE_URL", "未設定")
env = os.getenv("ENV", "development")

# データベース接続ヘルスチェック
db_status = get_db_health_check()

# サイドバー
with st.sidebar:
    st.header("設定メニュー")
    if st.button("ホームに戻る"):
        st.switch_page("pages/01_ホーム.py")

# メインコンテンツ
st.subheader("現在のデータベース設定")

# データベース種別と状態を表示
col1, col2 = st.columns(2)
with col1:
    st.info(f"DB種別: {db_status['type']}")
with col2:
    if db_status['status'] == 'healthy':
        st.success(f"接続状態: 正常 (レイテンシ: {db_status['latency_ms']}ms)")
    else:
        st.error(f"接続状態: エラー ({db_status.get('error', '不明なエラー')})")

# 現在の接続情報
st.subheader("接続情報")
if db_url.startswith("sqlite:///"):
    st.code(db_url, language="plaintext")
    st.caption("SQLiteデータベースを使用しています")
else:
    # PostgreSQL接続文字列はセキュリティのため一部を隠す
    masked_url = db_url
    if "://" in db_url and "@" in db_url:
        parts = db_url.split("@")
        auth_part = parts[0].split("://")
        if len(auth_part) > 1:
            username_password = auth_part[1].split(":")
            if len(username_password) > 1:
                masked_url = f"{auth_part[0]}://{username_password[0]}:****@{parts[1]}"
    
    st.code(masked_url, language="plaintext")
    st.caption("Railway PostgreSQLデータベースを使用しています")

# Railway設定手順
with st.expander("Railway PostgreSQLの設定手順", expanded=False):
    st.markdown("""
    ## Railwayでの設定手順

    ### 1. Railwayにサインアップ
    - [Railway公式サイト](https://railway.app/) にアクセス
    - GitHubでサインアップ（推奨）

    ### 2. 新規プロジェクトの作成
    1. 「New Project」をクリック
    2. 「Provision PostgreSQL」を選択
    3. デプロイが完了するまで待ちます（数秒）

    ### 3. 接続情報の取得
    1. プロジェクトダッシュボードの「PostgreSQL」を開く
    2. 「Connect」タブを開く
    3. 「Postgres Connection URL」をコピー

    ### 4. アプリケーションへの設定
    1. `.env`ファイルを開く
    2. 以下のように設定を書き換える:
       ```
       DATABASE_URL=postgresql://postgres:password@containers-us-west-123.railway.app:7890/railway
       ENV=production
       ```
    3. アプリケーションを再起動
    """)

# 環境切り替えの説明
st.subheader("開発環境 / 本番環境の切り替え")
st.write("現在の環境:", f"**{env.upper()}**")

st.markdown("""
現在の環境を変更するには、`.env`ファイルの`ENV`の値を変更します:

```
# 開発環境（SQLite）
ENV=development

# 本番環境（Railway PostgreSQL）
ENV=production
```

また、`.env`ファイルの`DATABASE_URL`を適切な接続文字列に設定してください。
""")

# データベースの移行と操作
with st.expander("データの移行と初期化", expanded=False):
    st.markdown("""
    ## データベースの移行と初期化

    ### SQLiteからPostgreSQLへのデータ移行
    1. SQLiteで作成したデータをCSVにエクスポート
    2. PostgreSQLにCSVからインポート

    ### データベース初期化
    **注意**: この操作は取り消せません。全てのデータが削除されます。

    1. SQLiteの場合: `shopping_app.db`ファイルを削除
    2. PostgreSQLの場合: Railwayコンソールから「Reset Database」を実行
    """)

