import streamlit as st
import pandas as pd
from datetime import datetime
from utils.ui_utils import show_header, show_success_message, show_error_message
from utils.ui_utils import check_authentication
from utils.db_utils import get_shopping_list, get_shopping_list_items, add_item_to_shopping_list
from utils.db_utils import update_shopping_list_item, get_stores, get_categories
from utils.db_utils import create_item, search_items, get_items_by_user, update_shopping_list
from utils.db_utils import remove_item_from_shopping_list

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

# リスト情報の編集機能
with st.expander("リスト情報を編集", expanded=False):
    with st.form("edit_list_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("リスト名", value=shopping_list.name)
        
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

# 前回選択したアイテムのカテゴリ情報を保持
if 'selected_item_category_id' not in st.session_state:
    st.session_state['selected_item_category_id'] = None

# 編集対象のアイテムIDをセッションに保存
if 'editing_item_id' not in st.session_state:
    st.session_state['editing_item_id'] = None

# カテゴリを自動設定する関数
def update_category_from_item(item_id):
    if not item_id:
        return
    
    # ユーザーのアイテム一覧を取得
    items = get_items_by_user(st.session_state.get('user_id'))
    
    # 選択したアイテムを探す
    selected_item = next((item for item in items if item.id == item_id), None)
    
    # 次回のレンダリングサイクルのためにカテゴリIDを保存
    if selected_item and selected_item.category_id:
        st.session_state.selected_item_category_id = str(selected_item.category_id)

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
    # 商品追加方法の選択
    input_method = st.radio("商品の追加方法", ["既存の商品から選択", "新しい商品を入力"], horizontal=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if input_method == "既存の商品から選択":
            # 既存の商品から選択する
            # カテゴリによるフィルタリング
            categories = get_categories(user_id=st.session_state.get('user_id'))
            category_options = ["すべてのカテゴリ"] + [c.name for c in categories]
            selected_category = st.selectbox("カテゴリで絞り込み", category_options, key="filter_category_select")
            
            # 商品データを取得してフィルタリング
            items = get_items_by_user(st.session_state.get('user_id'))
            filtered_items = items
            
            if selected_category != "すべてのカテゴリ":
                filtered_items = [item for item in items if item.category and item.category.name == selected_category]
            
            if filtered_items:
                # 商品を選択するセレクトボックスの選択肢を生成
                item_options = []
                for item in filtered_items:
                    category_name = item.category.name if item.category else "未分類"
                    item_options.append((str(item.id), f"{item.name} ({category_name})"))
                
                # 商品選択
                selected_item_id = st.selectbox(
                    "商品を選択", 
                    options=[id for id, _ in item_options],
                    format_func=lambda x: dict(item_options).get(x, ""),
                    key="select_existing_item"
                )
                
                if selected_item_id:
                    # 選択されたアイテム情報を表示
                    selected_item = next((item for item in filtered_items if str(item.id) == selected_item_id), None)
                    if selected_item:
                        category_name = selected_item.category.name if selected_item.category else "未分類"
                        st.write(f"**カテゴリ:** {category_name}")
                        
                        # フォーム送信時に選択された商品のカテゴリを設定
                        update_category_from_item(int(selected_item_id))
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
                planned_price=planned_price if planned_price > 0 else None
            )
            
            if list_item:
                show_success_message(f"{list_item.item.name if list_item.item else item_name}をリストに追加しました")
                
                # 反復処理の確認ダイアログを表示
                continue_adding = st.success("反復処理を続行しますか?")
                
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.form_submit_button("はい", use_container_width=True):
                        st.rerun()  # フォームをリセットして続行
                with col_no:
                    if st.form_submit_button("いいえ", use_container_width=True):
                        # 何もせずに終了（フォームはそのまま）
                        pass
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
            
            col3, col4 = st.columns(2)
            
            with col3:
                # 更新ボタン
                if st.form_submit_button("変更を保存"):
                    updated_item = update_shopping_list_item(
                        item_id=edit_item.id,
                        quantity=edit_quantity,
                        planned_price=edit_planned_price if edit_planned_price > 0 else None,
                        store_id=int(edit_store_id) if edit_store_id else None
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
        
        # カテゴリでフィルタリング機能を追加
        categories_in_list = sorted(df["カテゴリ"].unique().tolist())
        filter_category = st.selectbox(
            "カテゴリで絞り込み", 
            ["すべてのカテゴリ"] + categories_in_list,
            key="filter_category_list"
        )
        
        # フィルタリングされたデータフレームを作成
        filtered_df = df.copy()  # ここでコピーを作成
        if filter_category != "すべてのカテゴリ":
            filtered_df = filtered_df[filtered_df["カテゴリ"] == filter_category]
            # フィルタリング後の小計を再計算
            filtered_total = filtered_df["合計"].sum()
            st.caption(f"{filter_category} 合計予定金額: ¥{filtered_total:,.0f}")
        
        # DataFrameの表示
        if not filtered_df.empty:
            edited_df = st.data_editor(
                filtered_df,
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
            
            # 選択用のセレクトボックスを追加
            available_items = filtered_df.copy()
            item_options = [(str(row["ID"]), f"{row['商品名']} ({row['カテゴリ']})") for _, row in available_items.iterrows()]
            
            selected_item_id = st.selectbox(
                "操作するアイテムを選択", 
                options=[id for id, _ in item_options],
                format_func=lambda x: dict(item_options).get(x, ""),
                key="select_item_to_action"
            )
            
            # アクションボタンのレイアウト
            st.write("アイテム操作：")
            
            # 3列レイアウトでボタンを配置
            cols = st.columns(3)
            
            # 編集ボタン
            if cols[0].button("選択したアイテムを編集"):
                if selected_item_id:
                    st.session_state['editing_item_id'] = int(selected_item_id)
                    st.rerun()
                else:
                    show_error_message("編集するアイテムを選択してください")
            
            # 削除ボタン処理をシンプルに修正
            if cols[1].button("選択したアイテムを削除", type="primary", use_container_width=True):
                if selected_item_id:
                    if remove_item_from_shopping_list(int(selected_item_id)):
                        show_success_message("アイテムをリストから削除しました")
                        st.rerun()
                    else:
                        show_error_message("アイテムの削除に失敗しました")
                else:
                    show_error_message("削除するアイテムを選択してください")
            
            # 編集内容を反映
            for i, row in edited_df.iterrows():
                # オリジナルのデータフレームから該当するIDの行を特定
                original_rows = df[df["ID"] == row["ID"]]
                if not original_rows.empty:
                    original_row = original_rows.iloc[0]
                    if (row["数量"] != original_row["数量"] or 
                        row["購入済"] != original_row["購入済"]):
                        update_shopping_list_item(
                            item_id=row["ID"],
                            quantity=row["数量"],
                            checked=row["購入済"]
                        )
        else:
            st.info(f"このカテゴリ（{filter_category}）に該当する商品はありません")
    
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
            
            # 店舗別タブでもアクションボタンを表示
            st.write("アイテム操作：")
            
            # 選択用のセレクトボックスを追加
            available_store_items = store_df.copy()
            store_item_options = [(str(row["ID"]), f"{row['商品名']} ({row['カテゴリ']})") for _, row in available_store_items.iterrows()]
            
            selected_store_item_id = st.selectbox(
                "操作するアイテムを選択", 
                options=[id for id, _ in store_item_options],
                format_func=lambda x: dict(store_item_options).get(x, ""),
                key=f"select_store_item_to_action_{store_name}"
            )
            
            # 3列レイアウトでボタンを配置
            store_cols = st.columns(3)
            
            # 編集ボタン
            store_key = f"store_{store_name}".replace(" ", "_")
            if store_cols[0].button("選択したアイテムを編集", key=f"edit_btn_{store_key}"):
                if selected_store_item_id:
                    st.session_state['editing_item_id'] = int(selected_store_item_id)
                    st.rerun()
                else:
                    show_error_message("編集するアイテムを選択してください")
            
            # 削除ボタン処理をシンプルに修正
            if store_cols[1].button("選択したアイテムを削除", key=f"delete_btn_{store_key}", type="primary", use_container_width=True):
                if selected_store_item_id:
                    if remove_item_from_shopping_list(int(selected_store_item_id)):
                        show_success_message("アイテムをリストから削除しました")
                        st.rerun()
                    else:
                        show_error_message("アイテムの削除に失敗しました")
                else:
                    show_error_message("削除するアイテムを選択してください")
            
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