import streamlit as st
from datetime import datetime
from utils.ui_utils import show_header, show_shopping_list_summary, show_connection_indicator
from utils.ui_utils import check_authentication, logout
from utils.db_utils import get_user_by_id, get_shopping_lists, create_shopping_list

# 認証チェック
if not check_authentication():
    st.stop()

# ユーザー情報取得
user = get_user_by_id(st.session_state['user_id'])

# ページ設定
st.set_page_config(
    page_title="買い物アプリ",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ヘッダー表示
show_header(f"ようこそ、{user.name}さん")

# データベース接続インジケータを表示（右下に固定表示）
show_connection_indicator()

# サイドバーにメニュー
with st.sidebar:
    st.header("メニュー")
    
    # リストの新規作成フォーム
    st.subheader("買い物リストを作成")
    with st.form("create_list_form"):
        list_name = st.text_input("リスト名", placeholder="〇月×日の買い物", 
                                  value=f"{datetime.now().strftime('%m月%d日')}の買い物")
        memo = st.text_area("メモ（任意）", placeholder="予算や買い物のポイントなど", max_chars=200)
        create_button = st.form_submit_button("作成")
        
        if create_button:
            if list_name:
                # リスト作成
                new_list = create_shopping_list(
                    user_id=st.session_state['user_id'],
                    memo=memo,
                    name=list_name  # 名前パラメータを追加
                )
                if new_list:
                    st.session_state['current_list_id'] = new_list.id
                    st.success(f"「{list_name}」を作成しました！")
                    st.rerun()
                else:
                    st.error("リストの作成に失敗しました")
            else:
                st.error("リスト名を入力してください")
    
    # 各種管理画面へのリンク
    st.subheader("管理")
    if st.button("🏪 店舗・カテゴリ管理", use_container_width=True):
        st.switch_page("pages/06_店舗・カテゴリ管理.py")
        
    if st.button("⚙️ データベース設定", use_container_width=True):
        st.switch_page("pages/05_データベース設定.py")
        
    # ログアウトボタン
    st.subheader("アカウント")
    if st.button("ログアウト", use_container_width=True):
        logout()
        st.rerun()

# メインコンテンツ
st.subheader("最近の買い物リスト")

# 買い物リスト一覧の取得
shopping_lists = get_shopping_lists(user.id, limit=10)

if shopping_lists:
    # リストを日付でグループ化して表示
    for i, shopping_list in enumerate(shopping_lists):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button(f"{shopping_list.name}", key=f"list_{shopping_list.id}", use_container_width=True):
                st.session_state['current_list_id'] = shopping_list.id
                st.switch_page("pages/02_リスト編集.py")
                
        with col2:
            # 集計情報を表示（金額、アイテム数）
            show_shopping_list_summary(shopping_list)
            
        if i < len(shopping_lists) - 1:
            st.divider()
else:
    st.info("買い物リストがありません。サイドバーから新しいリストを作成してください。")

# 使い方ガイドを表示
with st.expander("💡 使い方ガイド", expanded=False):
    st.markdown("""
    ### 買い物アプリの使い方
    
    #### 基本的な流れ
    1. **買い物リストの作成**: サイドバーからリスト名を入力して作成します
    2. **商品の追加**: リスト編集ページで商品を追加します
    3. **買い物時**: 店舗別リストで商品をチェックしながら買い物します
    4. **履歴確認**: 支出分析で買い物の傾向を確認できます
    
    #### 便利な機能
    - **カテゴリ分類**: 商品をカテゴリで分類して管理できます
    - **複数店舗対応**: 一つのリストで複数の店舗の商品を管理できます
    - **支出分析**: カテゴリ別・店舗別の支出を分析できます
    
    #### カスタマイズ
    - **店舗の追加**: よく行く店舗を登録できます
    - **カテゴリの追加**: オリジナルのカテゴリを作成できます
    """)
    
# 更新情報
st.sidebar.markdown("---")
st.sidebar.caption("🆕 最近の更新")
st.sidebar.caption("・店舗・カテゴリ管理機能を追加")
st.sidebar.caption("・複数店舗対応を強化")
st.sidebar.caption("・Railway PostgreSQLサポート")
st.sidebar.caption(f"最終更新: 2025年4月17日")