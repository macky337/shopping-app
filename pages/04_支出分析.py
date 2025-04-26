import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from utils.ui_utils import show_header, show_spending_chart
from utils.ui_utils import check_authentication, show_connection_indicator
from utils.db_utils import get_user_purchases, get_category_spending, get_store_spending, update_purchase_date
from utils.ui_utils import patch_dark_background

# 認証チェック
if not check_authentication():
    st.stop()

# ページ設定
st.set_page_config(
    page_title="支出分析 | 買い物アプリ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

patch_dark_background()


# ヘッダー表示
show_header("支出分析 📊")

# サイドバー
with st.sidebar:
    st.header("メニュー")
    if st.button("ホームに戻る", use_container_width=True):
        st.switch_page("pages/01_ホーム.py")
    
    # 期間選択
    st.subheader("期間選択")
    period_option = st.radio(
        "表示期間",
        options=["過去7日", "過去30日", "過去3ヶ月", "今年", "すべて", "カスタム"],
        index=2
    )
    
    # 期間の計算
    today = datetime.now()
    
    if period_option == "過去7日":
        start_date = today - timedelta(days=7)
        end_date = today
    elif period_option == "過去30日":
        start_date = today - timedelta(days=30)
        end_date = today
    elif period_option == "過去3ヶ月":
        start_date = today - timedelta(days=90)
        end_date = today
    elif period_option == "今年":
        start_date = datetime(today.year, 1, 1)
        end_date = today
    elif period_option == "すべて":
        start_date = datetime(2020, 1, 1)  # 十分古い日付
        end_date = today
    else:  # カスタム
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input(
                "開始日",
                value=today - timedelta(days=90)
            )
        with date_col2:
            end_date = st.date_input(
                "終了日",
                value=today
            )
        # datetime型に変換
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())

    # 表示形式選択
    st.subheader("グラフ設定")
    chart_type = st.radio("チャートタイプ", ["棒グラフ", "円グラフ"], horizontal=True)
    chart_type = "bar" if chart_type == "棒グラフ" else "pie"

# メインコンテンツ - タブで分析種類を切り替え
tab1, tab2, tab3 = st.tabs(["カテゴリ別支出", "店舗別支出", "購入履歴"])

with tab1:
    st.subheader("カテゴリ別支出分析")
    
    # カテゴリ別支出データを取得
    category_spending = get_category_spending(
        user_id=st.session_state['user_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    # グラフ表示
    if category_spending:
        # 期間の合計金額を計算
        total_spending = sum(item['total_spending'] for item in category_spending)
        
        # 合計金額を表示
        st.metric("合計支出", f"¥{total_spending:,.0f}")
        
        # グラフ表示
        show_spending_chart(category_spending, chart_type)
        
        # データをテーブル表示
        st.subheader("詳細データ")
        
        # DataFrameに変換
        df = pd.DataFrame(category_spending)
        df = df.rename(columns={"category": "カテゴリ", "total_spending": "支出金額"})
        df["支出割合"] = df["支出金額"] / total_spending * 100
        
        # テーブル表示
        st.dataframe(
            df,
            column_config={
                "カテゴリ": st.column_config.TextColumn("カテゴリ"),
                "支出金額": st.column_config.NumberColumn("支出金額", format="¥%d"),
                "支出割合": st.column_config.NumberColumn("支出割合", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("選択した期間の購入データがありません")

with tab2:
    st.subheader("店舗別支出分析")
    
    # 店舗別支出データを取得
    store_spending = get_store_spending(
        user_id=st.session_state['user_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    # グラフ表示
    if store_spending:
        # 期間の合計金額を計算
        total_spending = sum(item['total_spending'] for item in store_spending)
        
        # 合計金額を表示
        st.metric("合計支出", f"¥{total_spending:,.0f}")
        
        # グラフデータ作成（category→storeに変更）
        chart_data = [{"category": item["store"], "total_spending": item["total_spending"]} for item in store_spending]
        
        # グラフ表示
        show_spending_chart(chart_data, chart_type)
        
        # データをテーブル表示
        st.subheader("詳細データ")
        
        # DataFrameに変換
        df = pd.DataFrame(store_spending)
        df = df.rename(columns={"store": "店舗名", "total_spending": "支出金額"})
        df["支出割合"] = df["支出金額"] / total_spending * 100
        
        # テーブル表示
        st.dataframe(
            df,
            column_config={
                "店舗名": st.column_config.TextColumn("店舗名"),
                "支出金額": st.column_config.NumberColumn("支出金額", format="¥%d"),
                "支出割合": st.column_config.NumberColumn("支出割合", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("選択した期間の購入データがありません")

with tab3:
    st.subheader("購入履歴一覧")
    
    # 購入履歴データを取得
    purchases = get_user_purchases(
        user_id=st.session_state['user_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    if purchases:
        # データをテーブル表示用に整形
        purchase_data = []
        for purchase in purchases:
            purchase_data.append({
                "id": purchase["id"],
                "日付": purchase["purchased_at"].strftime("%Y/%m/%d"),
                "商品名": purchase["item_name"],
                "カテゴリ": purchase.get("category_name", "未分類"),
                "店舗名": purchase.get("store_name", "未指定"),
                "単価": purchase["actual_price"] if purchase["actual_price"] is not None else 0,
                "数量": purchase["quantity"] if purchase["quantity"] is not None else 0,
                "合計": purchase["total"] if purchase["total"] is not None else (purchase["actual_price"] or 0) * (purchase["quantity"] or 0),
                "purchased_at": purchase["purchased_at"]
            })
        
        # DataFrameに変換
        df = pd.DataFrame(purchase_data)
        
        # 合計金額を計算
        total_amount = df["合計"].sum()
        st.metric("合計支出", f"¥{total_amount:,.0f}")
        
        # 編集UI
        st.write("### 日付編集")
        for row in purchase_data:
            with st.expander(f"{row['日付']} | {row['商品名']} | {row['店舗名']}"):
                new_date = st.date_input(
                    f"購入日付を編集（ID: {row['id']}）",
                    value=row["purchased_at"].date(),
                    key=f"date_input_{row['id']}"
                )
                if st.button("保存", key=f"save_btn_{row['id']}"):
                    dt = datetime.combine(new_date, row["purchased_at"].time())
                    success = update_purchase_date(row["id"], dt)
                    if success:
                        st.success("日付を更新しました。ページを再読み込みしてください。")
                    else:
                        st.error("日付の更新に失敗しました。")
        
        # テーブル表示
        st.dataframe(
            df.drop(columns=["id", "purchased_at"]),
            column_config={
                "日付": st.column_config.TextColumn("日付"),
                "商品名": st.column_config.TextColumn("商品名"),
                "カテゴリ": st.column_config.TextColumn("カテゴリ"),
                "店舗名": st.column_config.TextColumn("店舗名"),
                "単価": st.column_config.NumberColumn("単価", format="¥%d"),
                "数量": st.column_config.NumberColumn("数量"),
                "合計": st.column_config.NumberColumn("合計", format="¥%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 日別集計グラフ
        st.subheader("日別支出推移")
        
        # 日付でグループ化して集計
        df_daily = df.groupby('日付')['合計'].sum().reset_index()
        
        # 日付順にソート
        df_daily['日付'] = pd.to_datetime(df_daily['日付'])
        df_daily = df_daily.sort_values('日付')
        df_daily['日付'] = df_daily['日付'].dt.strftime('%Y/%m/%d')
        
        # 日ごとの合計額をテーブル表示
        st.dataframe(
            df_daily,
            column_config={
                "日付": st.column_config.TextColumn("日付"),
                "合計": st.column_config.NumberColumn("合計", format="¥%d"),
            },
            hide_index=True,
            use_container_width=True
        )

        # グラフ表示
        chart = alt.Chart(df_daily).mark_line(point=True).encode(
            x=alt.X('日付:N', title='日付', sort=None),
            y=alt.Y('合計:Q', title='支出金額(円)'),
            tooltip=['日付', alt.Tooltip('合計:Q', title='金額(円)', format=',')]
        ).properties(
            title='日別支出推移',
            width=600
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("選択した期間の購入データがありません")