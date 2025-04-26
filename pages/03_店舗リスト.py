import streamlit as st
from utils.ui_utils import show_header, show_success_message, show_error_message, show_hamburger_menu, show_bottom_nav
from utils.ui_utils import check_authentication, show_connection_indicator, patch_dark_background
from utils.db_utils import get_shopping_list, get_shopping_list_items, update_shopping_list_item
from utils.db_utils import get_stores, record_purchase

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
    page_title="店舗リスト | 買い物アプリ",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

patch_dark_background()


# リスト情報の取得
shopping_list = get_shopping_list(st.session_state['current_list_id'])

# 買い物リストが見つからない場合
if shopping_list is None:
    st.error("指定された買い物リストが見つかりませんでした")
    if st.button("ホームに戻る"):
        st.switch_page("pages/01_ホーム.py")
    st.stop()

list_items = get_shopping_list_items(shopping_list.id)

# ヘッダー表示
show_header(f"{shopping_list.name} - 買い物モード")

# 折りたたみ式メニュー
show_hamburger_menu()

# メインコンテンツ - 店舗別タブを作成
if list_items:
    # 店舗情報を取得
    store_items = {}
    no_store_items = []
    
    # アイテムを店舗ごとに分類
    for item in list_items:
        store_name = "未指定の店舗"
        if item.store:
            store_name = item.store.name
            
        if store_name not in store_items:
            store_items[store_name] = []
            
        store_items[store_name].append(item)
    
    # タブを作成
    store_names = list(store_items.keys())
    tabs = st.tabs(store_names)
    
    # 各店舗のタブ内容を作成
    for i, store_name in enumerate(store_names):
        with tabs[i]:
            items = store_items[store_name]
            checked_items = sum(1 for item in items if item.checked)
            
            # 進捗バー
            st.caption(f"進捗: {checked_items}/{len(items)} アイテム")
            progress = checked_items / len(items) if len(items) > 0 else 0
            # 緑色のカスタムプログレスバー
            bar_html = f'''
            <div style="background-color:#e0e0e0;border-radius:8px;width:100%;height:22px;">
                <div style="width:{progress*100:.1f}%;background-color:#4CAF50;height:100%;border-radius:8px;text-align:center;color:white;font-weight:bold;line-height:22px;">
                    {progress*100:.1f}%
                </div>
            </div>
            '''
            st.markdown(bar_html, unsafe_allow_html=True)
            
            # アイテム一覧をカテゴリごとにグループ化
            categories = {}
            for item in items:
                category_name = "未分類"
                if item.item and item.item.category:
                    category_name = item.item.category.name
                
                if category_name not in categories:
                    categories[category_name] = []
                    
                categories[category_name].append(item)
            
            # カテゴリごとに表示
            for category_name, category_items in categories.items():
                with st.expander(f"{category_name} ({len(category_items)}アイテム)", expanded=True):
                    for item in category_items:
                        col1, col2, col3, col4 = st.columns([0.5, 2, 1, 1])
                        
                        with col1:
                            # チェックボックス
                            checked = st.checkbox("", value=item.checked, key=f"check_{item.id}")
                            if checked != item.checked:
                                update_shopping_list_item(item.id, checked=checked)
                                st.rerun()
                        
                        with col2:
                            # 商品名と数量
                            item_name = item.item.name if item.item else "不明なアイテム"
                            st.write(f"{item_name} (×{item.quantity})")
                        
                        with col3:
                            # 予定金額
                            planned_price = item.planned_price if item.planned_price is not None else 0
                            st.write(f"¥{planned_price * (item.quantity if item.quantity is not None else 0):,.0f}")
                        
                        with col4:
                            # 購入処理ボタン
                            if st.button("購入記録", key=f"buy_{item.id}"):
                                st.session_state[f"record_purchase_{item.id}"] = True
                                st.rerun()
                            
                            # 購入記録モーダル
                            if st.session_state.get(f"record_purchase_{item.id}"):
                                with st.popover("購入金額を記録"):
                                    actual_price = st.number_input(
                                        "実際の金額", 
                                        value=float(item.planned_price) if item.planned_price is not None else 0,
                                        step=1.0,
                                        key=f"price_{item.id}"
                                    )
                                    
                                    quantity = st.number_input(
                                        "数量",
                                        value=item.quantity if item.quantity is not None else 1,
                                        min_value=1,
                                        step=1,
                                        key=f"qty_{item.id}"
                                    )
                                    
                                    col_a, col_b = st.columns(2)
                                    
                                    with col_a:
                                        if st.button("キャンセル", key=f"cancel_{item.id}"):
                                            del st.session_state[f"record_purchase_{item.id}"]
                                            st.rerun()
                                            
                                    with col_b:
                                        if st.button("記録する", key=f"save_{item.id}"):
                                            purchase = record_purchase(
                                                shopping_list_item_id=item.id,
                                                actual_price=actual_price,
                                                quantity=quantity
                                            )
                                            
                                            if purchase:
                                                show_success_message("購入記録を保存しました")
                                                del st.session_state[f"record_purchase_{item.id}"]
                                                st.rerun()
                                            else:
                                                show_error_message("購入記録の保存に失敗しました")
                        
                        st.divider()
else:
    st.info("このリストには商品が登録されていません。リスト編集画面から商品を追加してください。")

# ページ下部にタブバーを追加
show_bottom_nav()

# 店舗名入力フィールド
st.text_input("店舗名", placeholder="店舗名を入力してください", label_visibility="visible")