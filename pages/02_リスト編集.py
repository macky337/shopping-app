import streamlit as st
import pandas as pd
from datetime import datetime
from utils.ui_utils import show_header, show_success_message, show_error_message, show_hamburger_menu, show_bottom_nav
from utils.ui_utils import check_authentication, show_connection_indicator
from utils.db_utils import get_shopping_list, get_shopping_list_items, add_item_to_shopping_list
from utils.db_utils import update_shopping_list_item, get_stores, get_categories
from utils.db_utils import create_item, search_items, get_items_by_user, update_shopping_list
from utils.db_utils import remove_item_from_shopping_list, delete_shopping_list_items, get_shopping_list_total
from utils.ui_utils import patch_dark_background

# アイコンマッピング
default_category_icons = {
    "野菜": "🥦", "果物": "🍎", "飲料": "🥤", "菓子": "🍪",
    # 必要に応じて追加
}
store_icon = "🏬"

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

patch_dark_background()



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

# リスト情報の編集機能
with st.expander("リスト情報を編集", expanded=False):
    with st.form("edit_list_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("リスト名", placeholder="リスト名を入力してください", label_visibility="visible")
        
        with col2:
            new_date = st.date_input("日付", value=shopping_list.date)
            
        new_memo = st.text_area("メモ", value=shopping_list.memo if shopping_list.memo else "")
        
        if st.form_submit_button("リスト情報を更新"):
            updated_list = update_shopping_list(
                list_id=shopping_list.id,
                name=new_name,
                memo=new_memo if new_memo else None,
                date=new_date
            )
            
            if updated_list:
                show_success_message("リスト情報を更新しました")
                st.rerun()
            else:
                show_error_message("リスト情報の更新に失敗しました")

# セッション状態の初期化
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

# 選択した既存アイテムのIDをセッションに保存
if 'selected_existing_item_id' not in st.session_state:
    st.session_state['selected_existing_item_id'] = None

# 複数アイテム選択用のセッション変数
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = []

# 前回選択したアイテムのカテゴリ情報を保持
if 'selected_item_category_id' not in st.session_state:
    st.session_state['selected_item_category_id'] = None

# 編集対象のアイテムIDをセッションに保存
if 'editing_item_id' not in st.session_state:
    st.session_state['editing_item_id'] = None

# チェックボックス選択状態を保存するセッション変数
if 'item_selection' not in st.session_state:
    st.session_state['item_selection'] = {}

# アイテム選択状態をリセットする関数
def reset_item_selection():
    st.session_state['item_selection'] = {}

# 選択済みアイテムIDを取得する関数
def get_selected_item_ids():
    return [item_id for item_id, selected in st.session_state['item_selection'].items() if selected]

# 既存商品選択時にカテゴリIDをセッションに設定する関数
def update_category_from_item(item_id: int):
    """
    選択された既存商品のカテゴリIDを次のレンダリングサイクル用にセッションに保存します
    """
    # ユーザーの品目一覧を取得
    items = get_items_by_user(st.session_state.get('user_id'))
    # 選択されたアイテムを検索
    selected_item = next((item for item in items if item.id == item_id), None)
    # カテゴリIDをセッションに保存
    if (selected_item and selected_item.category_id):
        st.session_state['selected_item_category_id'] = str(selected_item.category_id)
    else:
        st.session_state['selected_item_category_id'] = None

# 折りたたみ式メニュー
show_hamburger_menu()

# メインコンテンツ
st.subheader("商品の追加")

"""
商品追加セクション (フォームを使用せず、動的に更新)
"""
add_item_container = st.container()
with add_item_container:
    # 商品追加方法の選択
    input_method = st.radio("商品の追加方法", ["既存の商品から選択", "新しい商品を入力"], horizontal=True)

    col1, col2 = st.columns(2)

    with col1:
        if input_method == "既存の商品から選択":
            # カテゴリ絞り込み用selectbox
            categories = get_categories(user_id=st.session_state.get('user_id'))
            category_options = ["すべてのカテゴリ"] + [c.name for c in categories]
            if 'filter_category' not in st.session_state:
                st.session_state['filter_category'] = "すべてのカテゴリ"
            # フィルタ変更時に既存商品の選択をクリアする
            def on_filter_category_change():
                st.session_state.pop('select_existing_item', None)
                st.session_state['selected_item_id'] = None
            selected_category = st.selectbox(
                "カテゴリで絞り込み", 
                category_options, 
                key="filter_category",
                on_change=on_filter_category_change
            )

            # カテゴリIDを取得
            selected_category_id = None
            if selected_category != "すべてのカテゴリ":
                selected_category_id = next((c.id for c in categories if c.name == selected_category), None)
                if selected_category_id is not None:
                    try:
                        selected_category_id = int(selected_category_id)
                    except Exception:
                        selected_category_id = None

            # DBレベルでカテゴリで絞り込む
            items = get_items_by_user(st.session_state.get('user_id'), category_id=selected_category_id)
            filtered_items = items

            if filtered_items:
                item_options = []
                for item in filtered_items:
                    category_name = item.category.name if item.category else "未分類"
                    item_options.append((str(item.id), f"{item.name} ({category_name})"))
                selection_label = "商品を選択"
                if selected_category != "すべてのカテゴリ":
                    selection_label = f"商品を選択 ({selected_category}のみ表示)"
                # 選択用selectboxのキーを固定
                select_item_key = 'select_existing_item'
                if len(item_options) > 0:
                    selected_item_id = st.selectbox(
                        selection_label, 
                        options=[id for id, _ in item_options],
                        format_func=lambda x: dict(item_options).get(x, ""),
                        key=select_item_key
                    )
                else:
                    st.info("選択したカテゴリに商品がありません")
                    selected_item_id = None
                if selected_item_id:
                    selected_item = next((item for item in filtered_items if str(item.id) == selected_item_id), None)
                    if selected_item:
                        category_name = selected_item.category.name if selected_item.category else "未分類"
                        st.write(f"**カテゴリ:** {category_name}")
                        update_category_from_item(int(selected_item_id))
                        st.session_state['selected_item_id'] = selected_item_id
            else:
                st.info("選択したカテゴリに商品がありません")
                selected_item_id = None
        
        # 新しい商品名入力（既存の商品がない場合、または新しい商品を入力する場合）
        if input_method == "新しい商品を入力":
            item_name = st.text_input("商品名", placeholder="りんご、牛乳など")
            selected_item_id = None
        else:
            # 既存の商品を選択する場合の初期化
            item_name = ""
        
        # カテゴリ選択
        categories = get_categories(user_id=st.session_state.get('user_id'))
        category_options = [("", "カテゴリを選択")] + [(str(c.id), c.name) for c in categories]
        
        # 選択されたアイテムからカテゴリを自動設定する（次のレンダリングサイクル用）
        default_category = st.session_state.get('selected_item_category_id', "")
        
        category_id = st.selectbox(
            "カテゴリ",
            options=[id for id, _ in category_options],
            format_func=lambda x: dict(category_options).get(x, "カテゴリを選択"),
            key="category_select",
            index=next((i for i, (id, _) in enumerate(category_options) if id == default_category), 0)
        )
        
        # 使用後にクリア
        if st.session_state.get('selected_item_category_id'):
            st.session_state.selected_item_category_id = None

        # 店舗選択
        stores = get_stores(user_id=st.session_state.get('user_id'))
        unique_stores = []
        seen_names = set()
        for s in stores:
            if s.name not in seen_names:
                unique_stores.append(s)
                seen_names.add(s.name)
        stores = unique_stores
        store_options = [("", "店舗を選択")] + [(str(s.id), s.name) for s in stores]
        store_id = st.selectbox(
            "購入予定店舗",
            options=[id for id, _ in store_options],
            format_func=lambda x: dict(store_options).get(x, "店舗を選択"),
            key="add_store_select"
        )
        
    with col2:
        # 予定金額
        # 既存商品選択時は前回金額をデフォルトに
        planned_price_default = 0
        if input_method == "既存の商品から選択" and st.session_state.get('selected_item_id'):
            from utils.db_utils import get_latest_planned_price
            user_id = st.session_state.get('user_id')
            item_id = int(st.session_state['selected_item_id'])
            latest_price = get_latest_planned_price(user_id, item_id)
            if (latest_price is not None):
                planned_price_default = latest_price
        planned_price = st.number_input("予定金額", min_value=0, step=10, value=int(planned_price_default))
    
        # 数量入力を追加
        quantity = st.number_input("数量", min_value=1, step=1, value=1)
    
    # 追加ボタン
    submit_button = st.button("リストに追加")
    
    if submit_button:
        if not item_name and input_method == "新しい商品を入力":
            show_error_message("商品名を入力してください")
        elif not selected_item_id and input_method == "既存の商品から選択":
            show_error_message("商品を選択してください")
        else:
            item_id = None
            
            if input_method == "既存の商品から選択" and selected_item_id:
                # 既存商品を使用
                item_id = int(selected_item_id)
                
                # フォーム送信時に選択された商品のカテゴリを設定
                update_category_from_item(item_id)
            else:
                # 既存アイテムの検索または新規作成
                items = search_items(st.session_state.get('user_id'), item_name)
                
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
                planned_price=planned_price if planned_price > 0 else None,
                quantity=int(quantity)
            )
            
            if list_item:
                show_success_message(f"{list_item.item.name if list_item.item else item_name}をリストに追加しました")
                # デフォルトで続行: 自動的に再レンダリング
                st.rerun()
            else:
                show_error_message("リストへの追加に失敗しました")

# アイテム編集フォーム
if st.session_state.get('editing_item_id'):
    st.subheader("商品の編集")
    
    # 編集対象のアイテムを取得
    items = get_shopping_list_items(shopping_list.id)
    edit_item = next((item for item in items if item.id == st.session_state['editing_item_id']), None)
    
    if edit_item:
        with st.form("edit_item_form"):
            st.write(f"**編集中の商品:** {edit_item.item.name if edit_item.item else '不明なアイテム'}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 予定金額
                edit_planned_price = st.number_input(
                    "予定金額", 
                    min_value=0.0, 
                    step=10.0, 
                    value=float(edit_item.planned_price) if edit_item.planned_price else 0.0
                )
            
            with col2:
                # 店舗選択
                stores = get_stores(user_id=st.session_state.get('user_id'))
                # 重複する店舗名を除去
                unique_stores = []
                seen_names = set()
                for s in stores:
                    if s.name not in seen_names:
                        unique_stores.append(s)
                        seen_names.add(s.name)
                stores = unique_stores
                store_options = [("", "店舗を選択")] + [(str(s.id), s.name) for s in stores]
                
                # 現在の店舗を選択
                current_store_index = 0
                if edit_item.store_id:
                    current_store_index = next(
                        (i for i, (id, _) in enumerate(store_options) if id == str(edit_item.store_id)), 
                        0
                    )
                
                edit_store_id = st.selectbox(
                    "購入予定店舗",
                    options=[id for id, _ in store_options],
                    format_func=lambda x: dict(store_options).get(x, "店舗を選択"),
                    index=current_store_index,
                    key="edit_store_select"
                )
            
            # 数量
            edit_quantity = st.number_input(
                "数量", 
                min_value=1, 
                step=1, 
                value=edit_item.quantity if edit_item.quantity else 1
            )
            # 日付編集を追加
            edit_planned_date = st.date_input(
                "予定日",
                value=edit_item.planned_date if edit_item.planned_date else datetime.today().date()
            )
            
            col3, col4 = st.columns(2)
            
            with col3:
                # 更新ボタン
                if st.form_submit_button("変更を保存"):
                    updated_item = update_shopping_list_item(
                        item_id=edit_item.id,
                        quantity=edit_quantity,
                        planned_price=edit_planned_price if edit_planned_price > 0 else None,
                        store_id=int(edit_store_id) if edit_store_id else None,
                        planned_date=edit_planned_date
                    )
                    
                    if updated_item:
                        show_success_message("アイテム情報を更新しました")
                        st.session_state['editing_item_id'] = None
                        st.rerun()
                    else:
                        show_error_message("アイテム情報の更新に失敗しました")
            
            with col4:
                # キャンセルボタン
                if st.form_submit_button("キャンセル"):
                    st.session_state['editing_item_id'] = None
                    st.rerun()
            
            # 合計金額の表示
            total_price = edit_quantity * edit_planned_price
            st.metric(label="合計金額", value=f"¥{total_price:,.0f}")

# 買い物リストの表示
st.subheader("現在のリスト")
# リスト全体の合計金額表示
list_totals = get_shopping_list_total(shopping_list.id)
st.metric(label="リスト合計金額", value=f"¥{list_totals['total_price']:,.0f}", delta=f"{list_totals['total_items']}点")

# 複数選択コントロールを追加
col_refresh, col_batch = st.columns([3, 1])
with col_batch:
    # 一括操作ボタンを追加
    if st.button("選択した商品を一括操作", use_container_width=True):
        st.session_state['show_batch_actions'] = True
    
# 一括操作セクションを表示
if st.session_state.get('show_batch_actions', False):
    selected_ids = get_selected_item_ids()
    
    if not selected_ids:
        st.warning("一括操作するアイテムが選択されていません")
        if st.button("閉じる"):
            st.session_state['show_batch_actions'] = False
    else:
        st.info(f"選択されたアイテム数: {len(selected_ids)}個")
        
        # 一括操作の種類を選択
        batch_action = st.radio("一括操作の種類", ["削除", "店舗変更", "日付変更"], horizontal=True)
        
        if batch_action == "削除":
            if st.button("選択した商品を一括削除", type="primary"):
                # 選択したアイテムを削除
                if delete_shopping_list_items(selected_ids):
                    show_success_message(f"{len(selected_ids)}個のアイテムを削除しました")
                    # 選択状態をリセット
                    reset_item_selection()
                    st.session_state['show_batch_actions'] = False
                    st.rerun()
                else:
                    show_error_message("アイテムの削除に失敗しました")
        
        elif batch_action == "店舗変更":
            # 店舗選択
            stores = get_stores(user_id=st.session_state.get('user_id'))
            # 重複する店舗名を除去
            unique_stores = []
            seen_names = set()
            for s in stores:
                if s.name not in seen_names:
                    unique_stores.append(s)
                    seen_names.add(s.name)
            stores = unique_stores
            store_options = [("", "店舗を選択")] + [(str(s.id), s.name) for s in stores]
            batch_store_id = st.selectbox(
                "新しい購入予定店舗",
                options=[id for id, _ in store_options],
                format_func=lambda x: dict(store_options).get(x, "店舗を選択"),
                key="batch_store_select"
            )
            
            if batch_store_id and st.button("店舗を一括変更", type="primary"):
                # 選択したアイテムの店舗を変更
                success_count = 0
                for item_id in selected_ids:
                    updated_item = update_shopping_list_item(
                        item_id=item_id,
                        store_id=int(batch_store_id) if batch_store_id else None
                    )
                    if updated_item:
                        success_count += 1
                
                if success_count > 0:
                    show_success_message(f"{success_count}個のアイテムの店舗を変更しました")
                    # 選択状態をリセット
                    reset_item_selection()
                    st.session_state['show_batch_actions'] = False
                    st.rerun()
                else:
                    show_error_message("アイテムの更新に失敗しました")
        
        elif batch_action == "日付変更":
            # 日付一括変更
            batch_date = st.date_input("新しい予定日を選択")
            if st.button("日付を一括変更", type="primary"):
                success_count = 0
                for item_id in selected_ids:
                    updated = update_shopping_list_item(
                        item_id=item_id,
                        planned_date=batch_date
                    )
                    if updated:
                        success_count += 1
                if success_count > 0:
                    show_success_message(f"{success_count}個のアイテムの予定日を変更しました")
                    reset_item_selection()
                    st.session_state['show_batch_actions'] = False
                    st.rerun()
                else:
                    show_error_message("予定日の更新に失敗しました")
        
        # 閉じるボタン
        if st.button("閉じる"):
            st.session_state['show_batch_actions'] = False
            st.rerun()

# リストアイテムを取得
items = get_shopping_list_items(shopping_list.id)

if items:
    # 元の数量を記録
    original_quantities = {item.id: item.quantity if item.quantity else 1 for item in items}
    # アイテムデータをDataFrameに変換
    item_data = []
    
    for item in items:
        # アイテム情報を取得
        store_name = item.store.name if item.store else "未指定"
        category_name = item.item.category.name if item.item and item.item.category else "未分類"
        
        # セッションにチェックボックスの初期状態を設定
        if item.id not in st.session_state['item_selection']:
            st.session_state['item_selection'][item.id] = False
        
        item_data.append({
            "選択": st.session_state['item_selection'][item.id],
            "ID": item.id,
            "商品名": item.item.name if item.item else "不明なアイテム",
            "カテゴリ": category_name,
            "数量": item.quantity if item.quantity else 1,
            "予定金額": item.planned_price if item.planned_price else "-",
            "予定日": item.planned_date if item.planned_date else "-",
            "購入価格": item.purchases[0].actual_price if item.purchases and len(item.purchases) > 0 else "-",
            "店舗": store_name,
            "購入済": "✓" if item.checked else "",
        })
    
    df = pd.DataFrame(item_data)
    if "予定日" in df.columns:
        # 予定日のフォーマットを指定して警告を回避
        df["予定日"] = pd.to_datetime(df["予定日"], format="%Y-%m-%d", errors="coerce")
        # NaN/NaT値の表示を改善
        df["予定日"] = df["予定日"].dt.date

    # チェックボックス列を追加したデータエディタを表示
    edited_df = st.data_editor(
        df,
        column_config={
            "選択": st.column_config.CheckboxColumn(
                "選択",  # ラベルを明示的に指定
                help="チェックを入れて一括操作できます",
                default=False,
            ),
            "ID": st.column_config.Column(
                "ID",
                disabled=True,
                required=True
            ),
            "商品名": st.column_config.Column(
                "商品名",
                disabled=True,
                required=True
            ),
            "カテゴリ": st.column_config.Column(
                "カテゴリ",
                disabled=True
            ),
            "数量": st.column_config.NumberColumn(
                "数量",
                disabled=False,
                help="数量を直接編集できます"
            ),
            "予定金額": st.column_config.NumberColumn(
                "予定金額",
                disabled=True
            ),
            "予定日": st.column_config.DateColumn(
                "予定日",
                disabled=False
            ),
            "購入価格": st.column_config.Column(
                "購入価格",
                disabled=True
            ),
            "店舗": st.column_config.Column(
                "店舗",
                disabled=True
            ),
            "購入済": st.column_config.Column(
                "購入済",
                disabled=True
            ),
        },
        hide_index=True,
        key="item_table"
    )
    
    # ❶ まず差分を検知
    selection_changed = (df["選択"] != edited_df["選択"]).any()

    # ❷ session_state を先に更新
    for _, row in edited_df.iterrows():
        st.session_state["item_selection"][row["ID"]] = row["選択"]

    # ❸ その後に rerun（必要なら）
    if selection_changed:
        st.rerun()

    # データエディタの再描画を条件付きで実行
    if any(df["選択"] != edited_df["選択"]):
        st.rerun()

    # チェックボックスの状態を更新
    for index, row in edited_df.iterrows():
        item_id = row["ID"]
        is_selected = row["選択"]
        # 状態が変化した場合のみセッションを更新
        if st.session_state['item_selection'].get(item_id) != is_selected:
            st.session_state['item_selection'][item_id] = is_selected

    # データフレームの選択状態をセッション状態に同期
    for item_id, is_selected in st.session_state['item_selection'].items():
        if item_id in df["ID"].values:
            df.loc[df["ID"] == item_id, "選択"] = is_selected

    # 数量変更と予定日変更をデータベースに反映
    for _, row in edited_df.iterrows():
        item_id = row["ID"]
        new_qty = row["数量"]
        old_qty = original_quantities.get(item_id)
        if new_qty != old_qty:
            updated = update_shopping_list_item(
                item_id=item_id,
                quantity=int(new_qty)
            )
            if updated:
                show_success_message(f"{updated.item.name if updated.item else ''} の数量を{new_qty}に更新しました")
        
        # 予定日変更反映 - NaT値のチェックを追加
        new_date = row.get("予定日")
        old_date = next((item.planned_date for item in items if item.id == item_id), None)
        
        # NaT値のチェック (pandas.NaTType は直接比較できないため、文字列変換で確認)
        is_valid_date = new_date is not None and str(new_date) != "NaT" and pd.notna(new_date)
        
        # 有効な日付のみを更新
        if is_valid_date and new_date != old_date:
            updated = update_shopping_list_item(
                item_id=item_id,
                planned_date=new_date
            )
            if updated:
                show_success_message(f"{updated.item.name if updated.item else ''} の予定日を{new_date}に更新しました")
    
    # アイテム操作用のボタン
    for item in items:
        item_name = item.item.name if item.item else "不明なアイテム"
        store_name = item.store.name if item.store else "未指定"
        
        with st.expander(f"{item_name} - {store_name}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("編集", key=f"edit_{item.id}", use_container_width=True):
                    st.session_state['editing_item_id'] = item.id
                    st.rerun()
            
            with col2:
                if st.button("削除", key=f"delete_{item.id}", use_container_width=True):
                    if remove_item_from_shopping_list(item.id):
                        show_success_message(f"{item_name}をリストから削除しました")
                        st.rerun()
                    else:
                        show_error_message("アイテムの削除に失敗しました")
            
            with col3:
                # 「購入済み」トグルボタン表示
                purchase_label = "購入取消" if item.checked else "購入済みにする"
                if st.button(purchase_label, key=f"purchase_{item.id}", use_container_width=True):
                    # 購入済みフラグを切り替え
                    updated_item = update_shopping_list_item(
                        item_id=item.id,
                        checked=not item.checked
                    )
                    
                    if updated_item:
                        status = "購入済み" if not item.checked else "未購入"
                        show_success_message(f"{item_name}を{status}に変更しました")
                        st.rerun()
                    else:
                        show_error_message("アイテム状態の更新に失敗しました")
else:
    st.info("リストにアイテムがありません。商品を追加してください。")

# 買い物リストがなくなった場合のクリーンアップ
def clear_current_list():
    if 'current_list_id' in st.session_state:
        del st.session_state['current_list_id']
    
    st.switch_page("pages/01_ホーム.py")

# リスト削除ボタン
with st.expander("リストの削除", expanded=False):
    st.warning("このリストを削除しますか？この操作は元に戻せません。")
    
    if st.button("リストを削除する", key="delete_list", use_container_width=True):
        # TODO: リスト削除処理を実装
        # ホーム画面に戻る
        clear_current_list()

# ページ下部にタブバーを追加
show_bottom_nav()