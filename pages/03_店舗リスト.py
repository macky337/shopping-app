import streamlit as st
from utils.ui_utils import show_header, show_success_message, show_error_message, show_hamburger_menu, show_bottom_nav
from utils.ui_utils import check_authentication, show_connection_indicator, patch_dark_background
from utils.db_utils import get_shopping_list, get_shopping_list_items, update_shopping_list_item, get_shopping_list_total, close_db_session, record_purchase, get_latest_planned_price

# 新規: チェックボックス変更ハンドラ
def handle_check(item_id):
    # DB更新とセッションリセット
    update_shopping_list_item(item_id, checked=st.session_state[f"check_{item_id}"])
    close_db_session()

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

# 合計金額表示
list_totals = get_shopping_list_total(shopping_list.id)
# 購入済み金額計算
purchase_total = sum(p.actual_price * p.quantity for item in list_items for p in item.purchases)
cols = st.columns(3)
cols[0].metric("リスト合計金額", f"¥{list_totals['total_price']:,.0f}")
cols[1].metric("チェック済み合計金額", f"¥{list_totals['checked_price']:,.0f}")
cols[2].metric("購入済み合計金額", f"¥{purchase_total:,.0f}")
# ステータス色分け凡例
st.markdown("""
**ステータス色分け:**  
<span style='background-color:#f8d7da;padding:4px;border-radius:4px;'>未チェック</span>  
<span style='background-color:#fff3cd;padding:4px;border-radius:4px;'>チェック済み</span>  
<span style='background-color:#d4edda;padding:4px;border-radius:4px;'>購入済み</span>
""", unsafe_allow_html=True)

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
                        # ステータスに応じた背景色
                        bgcolor = "#f8d7da"  # 未チェック
                        if item.purchases:
                            bgcolor = "#d4edda"  # 購入済み
                        elif item.checked:
                            bgcolor = "#fff3cd"  # チェック済み
                        # カラフルな背景でアイテム表示
                        st.markdown(f"<div style='background-color:{bgcolor}; padding:8px; border-radius:5px; margin-bottom:8px;'>", unsafe_allow_html=True)
                        cols = st.columns([0.5, 2, 1, 1])
                        with cols[0]:
                            # チェックボックス（on_changeでDB更新）
                            st.checkbox(
                                "",
                                value=item.checked,
                                key=f"check_{item.id}",
                                on_change=handle_check,
                                args=(item.id,)
                            )
                        with cols[1]:
                            item_name = item.item.name if item.item else "不明なアイテム"
                            st.write(f"{item_name} (×{item.quantity})")
                        with cols[2]:
                            # 予定金額フォールバック: リスト上の値(>0) → 商品デフォルト価格(>0) → 過去リストの直近予定価格
                            if item.planned_price is not None and item.planned_price > 0:
                                planned_price = item.planned_price
                            elif item.item and getattr(item.item, 'default_price', None) is not None and item.item.default_price > 0:
                                planned_price = item.item.default_price
                            else:
                                user_id = st.session_state.get('user_id')
                                planned_price = get_latest_planned_price(user_id, item.item.id) if item.item else 0
                            st.write(f"¥{planned_price * (item.quantity or 0):,.0f}")
                        with cols[3]:
                            if st.button("購入記録", key=f"buy_{item.id}"):
                                st.session_state[f"record_purchase_{item.id}"] = True
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                        # 続き: div 内での購入記録モーダルなど
                        if st.session_state.get(f"record_purchase_{item.id}"):
                            with st.container():
                                with st.form(key=f"purchase_form_{item.id}"):
                                    st.subheader("購入金額を記録")
                                    # デフォルト購入金額: リスト上の予定価格 or 商品デフォルト価格 or 直近予定価格
                                    if item.planned_price and item.planned_price > 0:
                                        default_price = item.planned_price
                                    elif item.item and getattr(item.item, 'default_price', None) and item.item.default_price > 0:
                                        default_price = item.item.default_price
                                    else:
                                        user_id = st.session_state.get('user_id')
                                        default_price = get_latest_planned_price(user_id, item.item.id) if item.item else 0
                                    # Decimal to float
                                    actual_price = st.number_input(
                                        "実際の金額", min_value=0.0, step=10.0,
                                        value=float(default_price),
                                        key=f"actual_{item.id}"
                                    )
                                    quantity_input = st.number_input(
                                        "数量", min_value=1, step=1,
                                        value=item.quantity or 1,
                                        key=f"qty_{item.id}"
                                    )
                                    if st.form_submit_button("記録する"):
                                        purchase = record_purchase(
                                            shopping_list_item_id=item.id,
                                            actual_price=actual_price,
                                            quantity=quantity_input
                                        )
                                        if purchase:
                                            show_success_message("購入記録を保存しました")
                                            del st.session_state[f"record_purchase_{item.id}"]
                                            st.rerun()
                                        else:
                                            show_error_message("購入記録の保存に失敗しました")
                                # キャンセルボタン（フォーム外）
                                if st.button("キャンセル", key=f"cancel_{item.id}"):
                                    del st.session_state[f"record_purchase_{item.id}"]
                                    st.rerun()
                            st.divider()
else:
    st.info("このリストには商品が登録されていません。リスト編集画面から商品を追加してください。")

# ページ下部にタブバーを追加
show_bottom_nav()