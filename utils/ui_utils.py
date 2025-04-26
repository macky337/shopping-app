import streamlit as st
from datetime import datetime
import json
import jwt
# モデルクラスをインポート
from .models import ShoppingList, Store, ShoppingListItem
from .db_utils import get_shopping_list_items, get_db_health_check
# 循環参照を避けるため、関数を直接インポートせず、必要な時に動的にインポートする

# アプリケーション情報
APP_VERSION = "1.2.0"
APP_LAST_UPDATED = "2025年4月20日"
APP_NAME = "買い物リスト管理アプリ BuyCheck"

# セッション管理
def init_session_state():
    """セッション状態の初期化"""
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'user_token' not in st.session_state:
        st.session_state['user_token'] = None
    if 'current_list_id' not in st.session_state:
        st.session_state['current_list_id'] = None
    if 'current_store_id' not in st.session_state:
        st.session_state['current_store_id'] = None
    
    # ページ読み込み時にトークンから認証を確認
    token = st.session_state.get('user_token')
    if token:
        from .db_utils import verify_jwt_token
        user_id = verify_jwt_token(token)
        if not user_id:
            # トークンが無効な場合はログアウト
            logout()
        else:
            st.session_state['user_id'] = user_id

def check_authentication():
    """認証のチェック。未認証ならログイン画面を表示"""
    # セッション状態を初期化してから認証チェック
    init_session_state()
    if 'user_id' not in st.session_state or not st.session_state['user_id']:
        show_login_screen()
        return False
    return True

def logout():
    """ログアウト処理"""
    from .db_utils import logout_user, close_db_session
    logout_user()
    for key in ['user_id', 'user_name', 'user_email', 'token', 'current_list_id']:
        if key in st.session_state:
            del st.session_state[key]
    close_db_session()
    return True

def get_current_user():
    """現在のユーザーオブジェクトを取得"""
    user_id = st.session_state.get('user_id')
    if not user_id:
        return None
    # 必要に応じて動的にインポート
    from .db_utils import get_user_by_id
    return get_user_by_id(user_id)

# UI表示関連
def show_header(title):
    """標準化されたヘッダーを表示"""
    st.title(title)
    st.divider()

def show_success_message(message):
    """成功メッセージを表示"""
    st.success(message)

def show_error_message(message):
    """エラーメッセージを表示"""
    st.error(message)

def show_warning_message(message):
    """警告メッセージを表示"""
    st.warning(message)

def show_login_screen():
    """ログイン・登録画面を表示"""
    st.title("買い物リスト管理アプリ BuyCheck 🛒")
    st.caption("ログインまたは新規登録してください")
    
    tab1, tab2 = st.tabs(["ログイン", "新規登録"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")
            password = st.text_input("パスワード", type="password")
            login_button = st.form_submit_button("ログイン")
            
            if login_button:
                if not email or not password:
                    st.error("メールアドレスとパスワードを入力してください")
                else:
                    from .db_utils import login_user
                    user = login_user(email, password)
                    if user:
                        st.session_state['user_id'] = user['user_id']
                        st.session_state['user_name'] = user['name']
                        st.session_state['user_email'] = user['email']
                        st.session_state['token'] = user['token']
                        st.rerun()
                    else:
                        st.error("メールアドレスまたはパスワードが間違っています")
    
    with tab2:
        with st.form("register_form"):
            name = st.text_input("お名前")
            email = st.text_input("メールアドレス", key="reg_email")
            password = st.text_input("パスワード", type="password", key="reg_password")
            password_conf = st.text_input("パスワード（確認）", type="password")
            register_button = st.form_submit_button("登録する")
            
            if register_button:
                if not name or not email or not password:
                    st.error("すべての項目を入力してください")
                elif password != password_conf:
                    st.error("パスワードが一致しません")
                else:
                    from .db_utils import register_user
                    user = register_user(email, password, name)
                    if user:
                        st.success("登録が完了しました！ログインしてください")
                    else:
                        st.error("登録に失敗しました。すでに使われているメールアドレスかもしれません")
    
    # ログイン画面のパフォーマンス改善のため、接続インジケータは一時非表示
    show_connection_indicator()

# 日付処理
def format_date(date_obj, format="%Y年%m月%d日"):
    """日付をフォーマットする"""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
    return date_obj.strftime(format)

def get_today():
    """今日の日付をdatetimeオブジェクトで取得する"""
    return datetime.now()

def get_today_str(format="%Y-%m-%d"):
    """今日の日付を文字列で取得する"""
    return datetime.now().strftime(format)

# データ表示
def show_shopping_list_card(shopping_list: ShoppingList):
    """買い物リストカードを表示する"""
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(shopping_list.name)
            st.caption(format_date(shopping_list.date))
        with col2:
            if st.button("表示", key=f"view_{shopping_list.id}"):
                st.session_state['current_list_id'] = shopping_list.id
                st.rerun()

def show_store_list_card(store: Store):
    """店舗カードを表示する"""
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(store.name)
        with col2:
            if st.button("表示", key=f"view_store_{store.id}"):
                st.session_state['current_store_id'] = store.id
                st.rerun()

def show_shopping_list_items(items: list[ShoppingListItem]):
    """買い物リストのアイテム一覧を表示"""
    if not items:
        st.info("リストにはまだ何も追加されていません")
        return
    
    # カテゴリでアイテムをグループ化
    categorized_items = {}
    for item in items:
        category = item.item.category.name if item.item and item.item.category else "未分類"
        if category not in categorized_items:
            categorized_items[category] = []
        categorized_items[category].append(item)
    
    # カテゴリごとに表示
    for category, category_items in categorized_items.items():
        with st.expander(f"{category} ({len(category_items)})", expanded=True):
            for item in category_items:
                col1, col2, col3 = st.columns([1, 5, 2])
                with col1:
                    checked = st.checkbox("", value=item.checked, key=f"check_{item.id}")
                    if checked != item.checked:
                        # チェック状態の変更を保存
                        from .db_utils import update_item_status
                        update_item_status(item.id, is_checked=checked)
                        st.rerun()
                with col2:
                    st.write(f"{item.item.name if item.item else '不明'} ({item.quantity} {'個'})")
                    if item.shopping_list.memo:
                        st.caption(item.shopping_list.memo)
                with col3:
                    if item.planned_price:
                        st.write(f"¥{item.planned_price:,.0f}")

def show_spending_chart(spending_data, chart_type="bar"):
    """支出分析チャートの表示"""
    import pandas as pd
    import altair as alt
    if not spending_data:
        st.info("表示できるデータがありません")
        return
        
    # データフレームに変換
    df = pd.DataFrame(spending_data)
    
    if chart_type == "bar":
        # 棒グラフ
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('category:N', title='カテゴリ', sort='-y'),
            y=alt.Y('total_spending:Q', title='支出金額(円)'),
            tooltip=['category', alt.Tooltip('total_spending:Q', title='金額(円)', format=',')]
        ).properties(
            title='カテゴリ別支出',
            width=600
        )
        st.altair_chart(chart, use_container_width=True)
        
    elif chart_type == "pie":
        # 円グラフ（Streamlitはネイティブの円グラフをサポートしていないので、Altairで作成）
        # 累積比率を計算
        total = df['total_spending'].sum()
        df['percentage'] = df['total_spending'] / total * 100
        
        pie = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(field="total_spending", type="quantitative"),
            color=alt.Color(field="category", type="nominal", legend=alt.Legend(title="カテゴリ")),
            tooltip=[
                alt.Tooltip('category:N', title='カテゴリ'),
                alt.Tooltip('total_spending:Q', title='金額(円)', format=','),
                alt.Tooltip('percentage:Q', title='割合(%)', format='.1f')
            ]
        ).properties(
            title='支出割合',
            width=400,
            height=400
        )
        st.altair_chart(pie, use_container_width=True)

def show_price_history(history_items):
    """価格履歴を表示する"""
    import pandas as pd
    import plotly.express as px
    if not history_items:
        st.info("価格履歴はありません")
        return
    
    # データフレームに変換
    history_data = []
    for item in history_items:
        history_data.append({
            "日付": item.recorded_date.strftime("%Y/%m/%d"),
            "価格": item.price,
            "店舗": item.store_name or "不明"
        })
    
    df = pd.DataFrame(history_data)
    
    # 履歴テーブル
    st.dataframe(df, use_container_width=True)
    
    # 履歴グラフ
    if len(df) > 1:
        fig = px.line(df, x="日付", y="価格", markers=True, title="価格推移")
        st.plotly_chart(fig, use_container_width=True)

def show_shopping_list_summary(shopping_list):
    """買い物リストのサマリーを表示（緑色カスタム進捗バー）"""
    items = get_shopping_list_items(shopping_list.id)
    total_items = len(items)
    checked_items = sum(1 for item in items if item.checked)
    total_price = sum((item.planned_price or 0) * item.quantity for item in items)
    progress_pct = 0
    if total_items > 0:
        progress_pct = checked_items / total_items
    st.caption(f"📊 予算: ¥{total_price:,.0f}")
    st.caption(f"✓ {checked_items}/{total_items} アイテム購入済")
    # --- 緑色カスタム進捗バー ---
    bar_width = int(progress_pct * 100)
    bar_html = f'''
    <div style="background:#e0e0e0;border-radius:8px;width:100%;height:18px;overflow:hidden;margin-bottom:4px;">
      <div style="background:#20d96b;height:100%;width:{bar_width}%;transition:width 0.3s;border-radius:8px;"></div>
    </div>
    <div style="font-size:12px;color:#20d96b;font-weight:bold;text-align:right;">{int(progress_pct*100)}%</div>
    '''
    st.markdown(bar_html, unsafe_allow_html=True)

def show_db_status():
    """データベース接続ステータスを表示"""
    # データベース接続状態を取得
    db_status = get_db_health_check()
    
    if db_status['status'] == 'healthy':
        st.success(f"データベース接続: 正常 ({db_status['type']})")
        col1, col2 = st.columns(2)
        col1.metric("レイテンシ", f"{db_status['latency_ms']}ms")
        col2.metric("環境", db_status['environment'])
    else:
        st.error(f"データベース接続エラー: {db_status.get('error', '不明なエラー')}")
        st.warning(f"データベースタイプ: {db_status['type']}")
        st.warning(f"環境: {db_status['environment']}")

# データベース接続インジケータを右下に表示
def show_connection_indicator():
    """データベース接続状態、バージョン情報、最終更新日を右下に表示する"""
    # 新しい CSS の定義（常に透過・境界線なし・色継承）
    indicator_style = """
    <style>
    .connection-indicator{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: inherit;
        font-size: 0.8em;
        max-width: 300px;
        margin: 10px 16px 0 auto;
        padding: 0;
        line-height: 1.4;
    }
    .connection-indicator .app-info{
        margin-top: 6px;
        border-top: 1px solid currentColor;
        opacity: .3;
        padding-top: 6px;
    }
    .healthy   { color: #20d96b !important; }
    .unhealthy { color: #ff5454 !important; }

    /* ───── スマホ幅（600px 以下）のときだけ左寄せ ───── */
    @media (max-width: 600px){
        .connection-indicator{
            margin: 10px 0 0 0; /* ← 左寄せ (右側 auto ではなく 0) */
            max-width: 100%;      /* 横幅いっぱいに           */
        }
    }
    </style>
    """
    # CSSを1回だけ注入
    if "indicator_css" not in st.session_state:
        st.markdown(indicator_style, unsafe_allow_html=True)
        st.session_state["indicator_css"] = True

    # データベース接続状態を取得
    db_status = get_db_health_check()
    status_class = "healthy" if db_status['status'] == 'healthy' else "unhealthy"
    status_icon = "✅" if db_status['status'] == 'healthy' else "❌"
    # HTMLの構築（スタイルは既に注入済み）
    html = f"""
    <div class="connection-indicator">
        <div>
            <span class="{status_class}">{status_icon} DB接続: {db_status['status']}</span>
            <span>({db_status['type']})</span>
        </div>
        <div>レイテンシ: {db_status.get('latency_ms', 'N/A')}ms</div>
        <div>環境: {db_status.get('environment', 'N/A')}</div>
        <div class="app-info">
            <div>{APP_NAME} v{APP_VERSION}</div>
            <div>最終更新日: {APP_LAST_UPDATED}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def show_hamburger_menu():
    """折りたたみ式サイドバーにナビゲーションメニューを表示"""
    with st.sidebar:
        with st.expander("≡ メニュー", expanded=False):
            if st.button("🏠 ホーム", use_container_width=True):
                st.switch_page("pages/01_ホーム.py")
            if st.button("📋 リスト", use_container_width=True):
                st.switch_page("pages/02_リスト編集.py")
            if st.button("📊 分析", use_container_width=True):
                st.switch_page("pages/04_支出分析.py")
            if st.button("⚙️ 設定", use_container_width=True):
                st.switch_page("pages/06_店舗・カテゴリ管理.py")

def show_bottom_nav():
    """画面下部に常時固定されるナビゲーション（st.button使用・認証維持・依存なし）"""
    st.markdown('''
    <style>
    .fixed-bottom-nav {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100vw;
        background: #f0f2f6;
        border-top: 1px solid #ccc;
        z-index: 9999;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
        padding: 0 0;
    }
    .fixed-bottom-nav-inner {
        display: flex;
        justify-content: space-around;
        align-items: center;
        height: 56px;
        max-width: 480px;
        margin: 0 auto;
    }
    .bottom-nav-btn {
        width: 100%;
        height: 56px;
        background: none;
        border: none;
        font-size: 13px;
        color: #333;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
    }
    .bottom-nav-btn .nav-icon { font-size: 22px; }
    </style>
    <div class="fixed-bottom-nav">
      <div class="fixed-bottom-nav-inner" id="st-bottom-nav"></div>
    </div>
    <script>
    // Streamlitのボタン配置用ダミーdiv
    const navDiv = window.parent.document.getElementById('st-bottom-nav');
    if(navDiv) navDiv.style.pointerEvents = 'none';
    </script>
    ''', unsafe_allow_html=True)
    # Streamlitのカラムでボタンを横並び
    cols = st.columns(4)
    with cols[0]:
        if st.button('ホーム', key='nav_home', use_container_width=True, help='ホーム'):
            st.switch_page('pages/01_ホーム.py')
        st.markdown('<div style="text-align:center;font-size:22px;">🏠</div><div style="text-align:center;">ホーム</div>', unsafe_allow_html=True)
    with cols[1]:
        if st.button('リスト', key='nav_list', use_container_width=True, help='リスト'):
            st.switch_page('pages/02_リスト編集.py')
        st.markdown('<div style="text-align:center;font-size:22px;">📋</div><div style="text-align:center;">リスト</div>', unsafe_allow_html=True)
    with cols[2]:
        if st.button('分析', key='nav_analysis', use_container_width=True, help='分析'):
            st.switch_page('pages/04_支出分析.py')
        st.markdown('<div style="text-align:center;font-size:22px;">📊</div><div style="text-align:center;">分析</div>', unsafe_allow_html=True)
    with cols[3]:
        if st.button('設定', key='nav_settings', use_container_width=True, help='設定'):
            st.switch_page('pages/06_店舗・カテゴリ管理.py')
        st.markdown('<div style="text-align:center;font-size:22px;">⚙️</div><div style="text-align:center;">設定</div>', unsafe_allow_html=True)

# カテゴリ関連
def get_category_options():
    """カテゴリ選択肢を取得する"""
    return [
        "食品", "飲料", "肉・魚", "野菜・果物", "乳製品", "冷凍食品", "調味料", "お菓子", "インスタント",
        "日用品", "衣類", "化粧品", "医薬品", "ペット用品", "文房具", "電化製品", "その他"
    ]

# ストア関連
def get_store_type_options():
    """店舗種別選択肢を取得する"""
    return [
        "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "デパート", 
        "ディスカウントストア", "専門店", "オンラインショップ", "その他"
    ]