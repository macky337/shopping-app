import streamlit as st
import pandas as pd
from utils.ui_utils import show_header, show_success_message, show_error_message
from utils.ui_utils import check_authentication, show_connection_indicator
from utils.db_utils import get_stores, get_categories, create_store, create_category

# 認証チェック
if not check_authentication():
    st.stop()

# ページ設定
st.set_page_config(
    page_title="店舗・カテゴリ管理 | 買い物アプリ",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データベース接続インジケータを表示
show_connection_indicator()

# ヘッダー表示
show_header("店舗・カテゴリ管理 🏪")

# サイドバー
with st.sidebar:
    st.header("メニュー")
    if st.button("ホームに戻る"):
        st.switch_page("pages/01_ホーム.py")

# メインコンテンツをタブで分ける
tab1, tab2 = st.tabs(["店舗管理", "カテゴリ管理"])

# 店舗管理タブ
with tab1:
    st.subheader("店舗の登録・管理")
    
    # 店舗一覧を取得
    stores = get_stores(st.session_state.get('user_id'))
    
    # 現在の店舗一覧を表示
    if stores:
        st.write("### 登録済みの店舗")
        # データフレーム用のデータを準備
        store_data = []
        for store in stores:
            store_type = "共有" if store.user_id is None else "個人"
            store_data.append({
                "ID": store.id,
                "店舗名": store.name,
                "種類": store.category or "",
                "タイプ": store_type
            })
        
        # データフレーム表示
        df = pd.DataFrame(store_data)
        st.dataframe(
            df,
            column_config={
                "店舗名": st.column_config.TextColumn("店舗名"),
                "種類": st.column_config.TextColumn("種類"),
                "タイプ": st.column_config.TextColumn("タイプ"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("登録された店舗はまだありません")
    
    # 新規店舗登録フォーム
    st.write("### 新しい店舗を登録")
    with st.form("store_form"):
        store_name = st.text_input("店舗名", placeholder="イオン、コストコなど")
        store_category = st.selectbox(
            "種類",
            options=["スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "デパート", "専門店", "その他"],
            index=None,
            placeholder="種類を選択してください"
        )
        
        submit_button = st.form_submit_button("登録する")
        
        if submit_button:
            if not store_name:
                show_error_message("店舗名を入力してください")
            else:
                new_store = create_store(
                    name=store_name,
                    category=store_category,
                    user_id=st.session_state.get('user_id')
                )
                
                if new_store:
                    show_success_message(f"{store_name}を店舗リストに登録しました")
                    st.rerun()
                else:
                    show_error_message("店舗の登録に失敗しました")

# カテゴリ管理タブ
with tab2:
    st.subheader("カテゴリの登録・管理")
    
    # カテゴリ一覧を取得
    categories = get_categories(st.session_state.get('user_id'))
    
    # 現在のカテゴリ一覧を表示
    if categories:
        st.write("### 登録済みのカテゴリ")
        # データフレーム用のデータを準備
        category_data = []
        # 同名カテゴリの重複排除用セット
        seen_names = set()
        for category in categories:
            # 名前で重複を除外
            if category.name in seen_names:
                continue
            seen_names.add(category.name)
            category_type = "共有" if category.user_id is None else "個人"
            category_data.append({
                "ID": category.id,
                "カテゴリ名": category.name,
                "タイプ": category_type
            })
        
        # データフレーム表示
        df = pd.DataFrame(category_data)
        st.dataframe(
            df,
            column_config={
                "カテゴリ名": st.column_config.TextColumn("カテゴリ名"),
                "タイプ": st.column_config.TextColumn("タイプ"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("登録されたカテゴリはまだありません")
    
    # 新規カテゴリ登録フォーム
    st.write("### 新しいカテゴリを登録")
    with st.form("category_form"):
        category_name = st.text_input("カテゴリ名", placeholder="野菜、肉類、日用品など")
        submit_button = st.form_submit_button("登録する")
        
        if submit_button:
            if not category_name:
                show_error_message("カテゴリ名を入力してください")
            else:
                new_category = create_category(
                    name=category_name,
                    user_id=st.session_state.get('user_id')
                )
                
                if new_category:
                    show_success_message(f"{category_name}をカテゴリリストに登録しました")
                    st.rerun()
                else:
                    show_error_message("カテゴリの登録に失敗しました")

# カテゴリと店舗の利用ガイド
with st.expander("カテゴリと店舗の管理について", expanded=False):
    st.markdown("""
    ### カテゴリと店舗の効果的な活用法
    
    #### カテゴリの活用
    1. **商品の分類**: カテゴリを使って商品を分類すると、買い物リストが整理されます
    2. **予算管理**: カテゴリごとの支出を追跡して、家計管理に役立てられます
    3. **買い物の効率化**: 同じカテゴリの商品をまとめて購入できます
    
    #### 店舗の活用
    1. **店舗別リスト**: 複数の店舗で買い物する場合、店舗別にリストを作成できます
    2. **価格比較**: 同じ商品の店舗による価格差を記録できます
    3. **ルート計画**: 訪問する店舗を事前に決めて効率的に買い物できます
    
    #### おすすめの設定
    - よく行く店舗は最初に登録しておきましょう
    - 自分だけのカテゴリを作成して、分類を細かくカスタマイズできます
    """)