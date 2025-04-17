import streamlit as st
import pandas as pd
from datetime import datetime
from utils.ui_utils import show_header, show_success_message, show_error_message
from utils.ui_utils import check_authentication
from utils.db_utils import get_shopping_list, get_shopping_list_items, add_item_to_shopping_list
from utils.db_utils import update_shopping_list_item, get_stores, get_categories
from utils.db_utils import create_item, search_items

# 認証チェック
if not check_authentication():
    st.stop()

# 買い物リストIDのチェック
if 'current_list_id' not in st.session_state:
    st.error("買い物リストが選択されていません")
    st.button("ホームに戻る", on_click=lambda: st.switch_page("pages/01_ホーム.py"))
    st.stop()

# ページ設定
st.set_page_config(
    page_title="リスト編集 | 買い物アプリ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# リスト情報の取得
shopping_list = get_shopping_list(st.session_state['current_list_id'])

# 買い物リストが見つからない場合
if shopping_list is None:
    st.error("指定された買い物リストが見つかりませんでした")
    if st.button("ホームに戻る"):
        st.switch_page("pages/01_ホーム.py")
    st.stop()

# ヘッダー表示
show_header(f"{shopping_list.name} の編集")

# セッション状態の初期化
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

# サイドバー
with st.sidebar:
    st.header("メニュー")
    if st.button("ホームに戻る", use_container_width=True):
        st.switch_page("pages/01_ホーム.py")
        
    if st.button("買い物モードへ", use_container_width=True):
        st.switch_page("pages/03_店舗リスト.py")
        
    # リスト情報を表示
    st.subheader("リスト情報")
    st.info(f"作成日: {shopping_list.date}")
    if shopping_list.memo:
        st.info(f"メモ: {shopping_list.memo}")

# メインコンテンツ
st.subheader("商品の追加")

# 商品追加フォーム
with st.form("add_item_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        # 商品名入力
        item_name = st.text_input("商品名", placeholder="りんご、牛乳など")
        
        # カテゴリ選択
        categories = get_categories(user_id=st.session_state.get('user_id'))
        category_options = [("", "カテゴリを選択")] + [(str(c.id), c.name) for c in categories]
        category_id = st.selectbox(
            "カテゴリ",
            options=[id for id, _ in category_options],
            format_func=lambda x: dict(category_options).get(x, "カテゴリを選択"),
            key="category_select"
        )
        
    with col2:
        # 予定金額
        planned_price = st.number_input("予定金額", min_value=0, step=10)
        
        # 店舗選択
        stores = get_stores(user_id=st.session_state.get('user_id'))
        store_options = [("", "店舗を選択")] + [(str(s.id), s.name) for s in stores]
        store_id = st.selectbox(
            "購入予定店舗",
            options=[id for id, _ in store_options],
            format_func=lambda x: dict(store_options).get(x, "店舗を選択"),
            key="store_select"
        )
    
    # 追加ボタン
    submit_button = st.form_submit_button("リストに追加")
    
    if submit_button:
        if not item_name:
            show_error_message("商品名を入力してください")
        else:
            # 既存アイテムの検索または新規作成
            items = search_items(st.session_state.get('user_id'), item_name)
            
            item_id = None
            if items:
                # 一致するアイテムが見つかった場合は最初のものを使用
                item_id = items[0].id
            else:
                # 新しいアイテムを作成
                new_item = create_item(
                    name=item_name,
                    user_id=st.session_state.get('user_id'),
                    category_id=int(category_id) if category_id else None,
                    default_price=planned_price if planned_price > 0 else None
                )
                if new_item:
                    item_id = new_item.id
                else:
                    show_error_message("アイテムの作成に失敗しました")
                    st.stop()
            
            # リストにアイテムを追加
            list_item = add_item_to_shopping_list(
                shopping_list_id=shopping_list.id,
                item_id=item_id,
                store_id=int(store_id) if store_id else None,
                planned_price=planned_price if planned_price > 0 else None
            )
            
            if list_item:
                show_success_message(f"{item_name}をリストに追加しました")
                st.rerun()
            else:
                show_error_message("リストへの追加に失敗しました")

# 買い物リストの表示
st.subheader("現在のリスト")

# リストアイテムを取得
items = get_shopping_list_items(shopping_list.id)

if items:
    # アイテムデータをDataFrameに変換
    item_data = []
    
    for item in items:
        # アイテム情報を取得
        store_name = item.store.name if item.store else "未指定"
        category_name = item.item.category.name if item.item and item.item.category else "未分類"
        
        item_data.append({
            "ID": item.id,
            "商品名": item.item.name if item.item else "不明なアイテム",
            "カテゴリ": category_name,
            "店舗": store_name,
            "予定金額": item.planned_price or 0,
            "数量": item.quantity,
            "合計": (item.planned_price or 0) * item.quantity,
            "購入済": item.checked
        })
    
    # DataFrameを作成
    df = pd.DataFrame(item_data)
    
    # 店舗別に分類して表示
    stores_in_list = df["店舗"].unique().tolist()
    
    tab_names = ["すべて"] + stores_in_list
    tabs = st.tabs(tab_names)
    
    # すべてのタブ
    with tabs[0]:
        # 小計を計算
        total = df["合計"].sum()
        st.caption(f"合計予定金額: ¥{total:,.0f}")
        
        # DataFrameの表示
        edited_df = st.data_editor(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", required=True),
                "商品名": st.column_config.TextColumn("商品名"),
                "カテゴリ": st.column_config.TextColumn("カテゴリ"),
                "店舗": st.column_config.TextColumn("店舗"),
                "予定金額": st.column_config.NumberColumn("予定金額", format="¥%d"),
                "数量": st.column_config.NumberColumn("数量", min_value=1, step=1),
                "合計": st.column_config.NumberColumn("合計", format="¥%d"),
                "購入済": st.column_config.CheckboxColumn("購入済")
            },
            hide_index=True,
            use_container_width=True,
            key="all_items",
            disabled=["ID", "商品名", "カテゴリ", "店舗", "合計"]  # 編集できない列
        )
        
        # 編集内容を反映
        for i, row in edited_df.iterrows():
            original_row = df.iloc[i]
            if (row["数量"] != original_row["数量"] or 
                row["購入済"] != original_row["購入済"]):
                update_shopping_list_item(
                    item_id=row["ID"],
                    quantity=row["数量"],
                    checked=row["購入済"]
                )
    
    # 店舗別タブ
    for i, store_name in enumerate(stores_in_list):
        with tabs[i+1]:
            # 店舗別にフィルタリング
            store_df = df[df["店舗"] == store_name].copy()
            
            # 小計を計算
            store_total = store_df["合計"].sum()
            st.caption(f"{store_name} 合計予定金額: ¥{store_total:,.0f}")
            
            # DataFrameの表示
            edited_store_df = st.data_editor(
                store_df,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", required=True),
                    "商品名": st.column_config.TextColumn("商品名"),
                    "カテゴリ": st.column_config.TextColumn("カテゴリ"),
                    "店舗": st.column_config.TextColumn("店舗"),
                    "予定金額": st.column_config.NumberColumn("予定金額", format="¥%d"),
                    "数量": st.column_config.NumberColumn("数量", min_value=1, step=1),
                    "合計": st.column_config.NumberColumn("合計", format="¥%d"),
                    "購入済": st.column_config.CheckboxColumn("購入済")
                },
                hide_index=True,
                use_container_width=True,
                key=f"store_{store_name}",
                disabled=["ID", "商品名", "カテゴリ", "店舗", "合計"]  # 編集できない列
            )
            
            # 編集内容を反映
            for j, row in edited_store_df.iterrows():
                original_index = df[df["ID"] == row["ID"]].index[0]
                original_row = df.iloc[original_index]
                if (row["数量"] != original_row["数量"] or 
                    row["購入済"] != original_row["購入済"]):
                    update_shopping_list_item(
                        item_id=row["ID"],
                        quantity=row["数量"],
                        checked=row["購入済"]
                    )
else:
    st.info("このリストにはまだアイテムがありません。上のフォームからアイテムを追加してください。")