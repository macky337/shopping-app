#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
買い物アプリの初期データ：一般的な品目を事前登録するスクリプト
"""

import os
import sys
from utils.db_utils import init_db, get_db_session, create_category, create_item

# デフォルトカテゴリの定義（ユーザーIDはNoneで登録 = 共通カテゴリ）
DEFAULT_CATEGORIES = [
    {"name": "野菜・果物", "items": [
        {"name": "にんじん", "default_price": 100},
        {"name": "じゃがいも", "default_price": 150},
        {"name": "たまねぎ", "default_price": 100},
        {"name": "トマト", "default_price": 150},
        {"name": "きゅうり", "default_price": 80},
        {"name": "なす", "default_price": 100},
        {"name": "キャベツ", "default_price": 200},
        {"name": "レタス", "default_price": 150},
        {"name": "ほうれん草", "default_price": 150},
        {"name": "りんご", "default_price": 150},
        {"name": "バナナ", "default_price": 100},
        {"name": "みかん", "default_price": 150},
        {"name": "ぶどう", "default_price": 400},
        {"name": "いちご", "default_price": 300},
    ]},
    {"name": "肉・魚", "items": [
        {"name": "豚肉（こま切れ）", "default_price": 300},
        {"name": "豚肉（ロース）", "default_price": 400},
        {"name": "牛肉（こま切れ）", "default_price": 400},
        {"name": "牛肉（ステーキ用）", "default_price": 800},
        {"name": "鶏肉（むね）", "default_price": 250},
        {"name": "鶏肉（もも）", "default_price": 350},
        {"name": "ひき肉", "default_price": 300},
        {"name": "刺身（まぐろ）", "default_price": 400},
        {"name": "鮭", "default_price": 300},
        {"name": "あじ", "default_price": 200},
        {"name": "さば", "default_price": 250},
    ]},
    {"name": "乳製品・卵", "items": [
        {"name": "牛乳", "default_price": 200},
        {"name": "ヨーグルト", "default_price": 150},
        {"name": "チーズ", "default_price": 300},
        {"name": "バター", "default_price": 250},
        {"name": "卵", "default_price": 200},
    ]},
    {"name": "調味料・油", "items": [
        {"name": "しょうゆ", "default_price": 300},
        {"name": "みそ", "default_price": 250},
        {"name": "砂糖", "default_price": 200},
        {"name": "塩", "default_price": 150},
        {"name": "こしょう", "default_price": 200},
        {"name": "サラダ油", "default_price": 300},
        {"name": "ごま油", "default_price": 350},
        {"name": "オリーブオイル", "default_price": 500},
        {"name": "酢", "default_price": 200},
    ]},
    {"name": "米・パン・麺", "items": [
        {"name": "お米", "default_price": 2000},
        {"name": "食パン", "default_price": 150},
        {"name": "うどん", "default_price": 200},
        {"name": "そば", "default_price": 200},
        {"name": "ラーメン", "default_price": 300},
        {"name": "パスタ", "default_price": 200},
    ]},
    {"name": "加工食品", "items": [
        {"name": "缶詰（ツナ）", "default_price": 150},
        {"name": "缶詰（コーン）", "default_price": 100},
        {"name": "レトルトカレー", "default_price": 250},
        {"name": "冷凍食品（ピザ）", "default_price": 500},
        {"name": "冷凍食品（餃子）", "default_price": 300},
        {"name": "冷凍食品（コロッケ）", "default_price": 250},
    ]},
    {"name": "飲料", "items": [
        {"name": "お茶", "default_price": 150},
        {"name": "コーヒー", "default_price": 300},
        {"name": "ジュース", "default_price": 150},
        {"name": "水", "default_price": 100},
    ]},
    {"name": "お菓子", "items": [
        {"name": "チョコレート", "default_price": 200},
        {"name": "ビスケット", "default_price": 150},
        {"name": "ポテトチップス", "default_price": 150},
        {"name": "アイスクリーム", "default_price": 250},
    ]},
    {"name": "日用品", "items": [
        {"name": "トイレットペーパー", "default_price": 300},
        {"name": "ティッシュペーパー", "default_price": 200},
        {"name": "洗剤", "default_price": 350},
        {"name": "シャンプー", "default_price": 500},
        {"name": "ボディーソープ", "default_price": 400},
        {"name": "歯磨き粉", "default_price": 200},
    ]},
]

def main():
    """メイン処理：カテゴリと商品アイテムを登録する"""
    print("デフォルトの品目をデータベースに登録しています...")
    
    # データベース初期化
    init_db()
    session = get_db_session()
    
    try:
        # カテゴリごとにアイテムを追加
        for category_info in DEFAULT_CATEGORIES:
            # カテゴリを作成（user_id=None でデフォルトカテゴリとして登録）
            category_name = category_info["name"]
            print(f"カテゴリ「{category_name}」を登録中...")
            category = create_category(category_name, user_id=None)
            
            if category:
                # カテゴリに紐づくアイテムを登録
                for item_info in category_info["items"]:
                    item_name = item_info["name"]
                    default_price = item_info["default_price"]
                    item = create_item(
                        name=item_name, 
                        user_id=None,  # user_id=None でデフォルトアイテムとして登録
                        category_id=category.id,
                        default_price=default_price
                    )
                    if item:
                        print(f"  - 「{item_name}」を登録しました（価格: {default_price}円）")
                    else:
                        print(f"  - 「{item_name}」の登録に失敗しました")
            else:
                print(f"カテゴリ「{category_name}」の登録に失敗しました")
        
        print("デフォルト品目の登録が完了しました！")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        # セッションを閉じる
        if 'db_session' in sys.modules:
            if hasattr(session, 'close'):
                session.close()

if __name__ == "__main__":
    main()