import os
import sqlite3
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# PostgreSQL接続情報 (Railway用)
PG_URL = os.getenv("DATABASE_URL")

def sqlite_to_postgres():
    """SQLiteからPostgreSQLにデータを移行する"""
    # SQLiteデータベースに接続
    sqlite_conn = sqlite3.connect('shopping_app.db')
    
    # テーブル一覧を取得
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", sqlite_conn)
    
    # PostgreSQL接続
    if not PG_URL:
        print("エラー: DATABASE_URL環境変数が設定されていません")
        return False
    
    try:
        pg_conn = psycopg2.connect(PG_URL)
        pg_cursor = pg_conn.cursor()
        
        # 各テーブルのデータを移行
        for table_name in tables['name']:
            # システムテーブルはスキップ
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"テーブル '{table_name}' の移行を開始...")
            
            # SQLiteからデータを取得
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", sqlite_conn)
            
            if len(df) == 0:
                print(f"  テーブル '{table_name}' にデータがありません。スキップします。")
                continue
                
            # データフレームのカラム名を取得
            columns = df.columns
            
            # 各行をPostgreSQLに挿入
            for _, row in df.iterrows():
                # 挿入用SQLクエリを作成
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join([f'"{col}"' for col in columns])
                
                # NULLをNoneに変換
                values = [None if pd.isna(x) else x for x in row]
                
                # UPSERTクエリ（行が存在する場合は更新、存在しない場合は挿入）
                upsert_query = f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders})
                ON CONFLICT (id) DO NOTHING
                """
                
                try:
                    pg_cursor.execute(upsert_query, values)
                except Exception as e:
                    print(f"  エラー: {table_name} テーブルへの挿入中にエラーが発生しました: {e}")
                    
            # コミット
            pg_conn.commit()
            print(f"  テーブル '{table_name}' の移行が完了しました。")
            
        pg_cursor.close()
        pg_conn.close()
        sqlite_conn.close()
        
        print("データ移行が完了しました！")
        return True
        
    except Exception as e:
        print(f"エラー: PostgreSQLへの接続/移行中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    print("SQLiteからPostgreSQLへのデータ移行を開始します...")
    success = sqlite_to_postgres()
    if success:
        print("移行が正常に完了しました。")
    else:
        print("移行中にエラーが発生しました。")

import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "ここに接続URLを直接書いてもOK")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE shopping_list_items ADD COLUMN IF NOT EXISTS planned_date DATE;")
conn.commit()
cur.close()
conn.close()
print("planned_dateカラムを追加しました")