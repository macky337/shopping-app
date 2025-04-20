import os
import sys
import psycopg2  # このインポート文を追加

# .envファイルを直接読み込む
env_file_path = ".env"
print(f".envファイルのパス: {os.path.abspath(env_file_path)}")

try:
    with open(env_file_path, "r", encoding="utf-8") as f:
        env_content = f.read()
        print("UTF-8で正常に読み込めました")
        
    # DATABASE_URLの行を探す
    for line in env_content.split("\n"):
        if line.startswith("DATABASE_URL="):
            # 安全のため最初と最後だけ表示
            url = line[13:]  # "DATABASE_URL="の後ろ
            if len(url) > 20:
                print(f"DATABASE_URL: {url[:10]}...{url[-10:]}")
            else:
                print(f"DATABASE_URL: {url}")
            break

except UnicodeDecodeError:
    print("UTF-8でデコードできませんでした。他のエンコーディングを試します...")
    
    try:
        with open(env_file_path, "r", encoding="shift-jis") as f:
            env_content = f.read()
            print("Shift-JISで読み込めました")
            
        # DATABASE_URLを探してASCII文字のみに修正
        new_env = []
        for line in env_content.split("\n"):
            if line.startswith("DATABASE_URL="):
                # ASCII文字のみに制限
                url = line[13:]
                ascii_url = ''.join(c for c in url if ord(c) < 128)
                new_env.append(f"DATABASE_URL={ascii_url}")
                print(f"修正したURL: {ascii_url[:10]}...{ascii_url[-10:]}")
            else:
                new_env.append(line)
                
        # 修正した.envファイルを保存
        with open(".env.fixed", "w", encoding="utf-8") as f:
            f.write("\n".join(new_env))
            print(".env.fixedファイルを作成しました。このファイルを.envにリネームしてください。")
    
    except Exception as e:
        print(f"エラー: {e}")

# .env から接続文字列を読み取る
DATABASE_URL = None
for line in env_content.split("\n"):
    if line.startswith("DATABASE_URL="):
        DATABASE_URL = line[13:]
        break
# 末尾や先頭の空白・改行を除去
DATABASE_URL = DATABASE_URL.strip()
# 改行文字が混入している場合に除去
DATABASE_URL = DATABASE_URL.replace('\n', '').replace('\r', '')

# 提案されたテーブル構造に基づくSQLコマンド
CREATE_TABLES_SQL = """
-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 店舗テーブル
CREATE TABLE IF NOT EXISTS stores (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, user_id)
);

-- カテゴリテーブル
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, user_id)
);

-- 品目テーブル
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    default_price NUMERIC,
    category_id INTEGER REFERENCES categories(id),
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, user_id)
);

-- 買い物リスト（親）
CREATE TABLE IF NOT EXISTS shopping_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 買い物リストアイテム
CREATE TABLE IF NOT EXISTS shopping_list_items (
    id SERIAL PRIMARY KEY,
    shopping_list_id INTEGER REFERENCES shopping_lists(id) NOT NULL,
    item_id INTEGER REFERENCES items(id),
    store_id INTEGER REFERENCES stores(id),
    planned_price NUMERIC,
    checked BOOLEAN DEFAULT FALSE,
    quantity INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 購入履歴
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    shopping_list_item_id INTEGER REFERENCES shopping_list_items(id) NOT NULL,
    actual_price NUMERIC NOT NULL,
    quantity INTEGER NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- デフォルトカテゴリの登録
INSERT INTO categories (name) VALUES 
    ('食品'),
    ('飲料'),
    ('生鮮食品'),
    ('冷凍食品'),
    ('日用品'),
    ('衣料品'),
    ('電化製品'),
    ('その他')
ON CONFLICT DO NOTHING;

-- デフォルト店舗の登録
INSERT INTO stores (name, category) VALUES 
    ('オリンピック', 'スーパー'),
    ('イオン', 'スーパー'),
    ('コストコ', 'ホールセール'),
    ('ニトリ', 'ホームセンター'),
    ('ドラッグストア', 'ドラッグストア')
ON CONFLICT DO NOTHING;
"""

try:
    # 接続の確認用にフルDSNを表示
    print(f"使用しているDATABASE_URL: {DATABASE_URL}")
    import socket
    from urllib.parse import urlparse
    # DSNからホストとポートを抽出
    parsed = urlparse(DATABASE_URL)
    host = parsed.hostname
    port = parsed.port or 5432
    print(f"ソケットレベル接続テスト: {host}:{port}")
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print("ソケット接続成功")
        sock.close()
    except Exception as sock_err:
        print(f"ソケット接続失敗: {sock_err}")

    # タイムアウトを5秒に設定して接続
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
    cur = conn.cursor()
    print("PostgreSQLに接続成功しました！")

    # テーブル作成
    cur.execute(CREATE_TABLES_SQL)
    conn.commit()
    print("テーブル作成成功")

    # ダミーデータ作成
    print("ダミーデータを挿入中...")
    # テストユーザー作成
    cur.execute(
        """
        INSERT INTO users (email, password_hash, name)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        ('test@example.com', 'testhash', 'テストユーザー')
    )
    conn.commit()
    cur.execute("SELECT id FROM users WHERE email=%s", ('test@example.com',))
    test_user_id = cur.fetchone()[0]

    # ダミーアイテム作成
    dummy_items = [
        ('りんご', 100, '生鮮食品'),
        ('牛乳', 200, '飲料'),
        ('卵', 150, '生鮮食品'),
        ('パン', 120, 'その他'),
        ('トイレットペーパー', 300, '日用品'),
    ]
    item_ids = []
    for name, price, category_name in dummy_items:
        cur.execute("SELECT id FROM categories WHERE name=%s", (category_name,))
        cat_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO items (name, default_price, category_id, user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (name, price, cat_id, test_user_id)
        )
        conn.commit()
        cur.execute(
            "SELECT id FROM items WHERE name=%s AND user_id=%s",
            (name, test_user_id)
        )
        item_ids.append(cur.fetchone()[0])

    # ダミー買い物リスト作成
    cur.execute(
        """
        INSERT INTO shopping_lists (user_id, date, memo)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (test_user_id, '2025-04-20', 'テスト用メモ')
    )
    list_id = cur.fetchone()[0]
    conn.commit()

    # リストアイテム挿入
    cur.execute("SELECT id FROM stores WHERE name=%s", ('イオン',))
    store_id = cur.fetchone()[0]
    for idx, item_id in enumerate(item_ids, start=1):
        cur.execute(
            """
            INSERT INTO shopping_list_items (shopping_list_id, item_id, store_id, planned_price, quantity)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (list_id, item_id, store_id, 100 * idx, idx)
        )
    conn.commit()

    # 購入履歴挿入 (最初のアイテムのみ)
    cur.execute(
        "SELECT id FROM shopping_list_items WHERE shopping_list_id=%s LIMIT 1",
        (list_id,)
    )
    sli_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO purchases (shopping_list_item_id, actual_price, quantity)
        VALUES (%s, %s, %s)
        """,
        (sli_id, 90, 1)
    )
    conn.commit()
    print("ダミーデータ作成完了。")

    # テーブル一覧を確認
    cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """)
    
    print("作成されたテーブル一覧:")
    for table in cur.fetchall():
        print(f"- {table[0]}")
    
    # テーブルの内容を確認
    tables = ['users', 'categories', 'stores', 'items', 'shopping_lists', 
              'shopping_list_items', 'purchases']
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count}件のデータ")
        
        if table in ['categories', 'stores'] and count > 0:
            cur.execute(f"SELECT * FROM {table} LIMIT 5")
            print(f"{table}のサンプルデータ:")
            for row in cur.fetchall():
                print(f"  {row}")

    # 後始末
    cur.close()
    conn.close()
    print("接続を閉じました")
    print("\n🎉 データベース初期化が完了しました！")
    
except Exception as e:
    print(f"エラー: {type(e).__name__}")
    print(f"詳細: {e}")