import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import bcrypt
import streamlit as st
from .models import Base, User, Store, Category, Item, ShoppingList, ShoppingListItem, Purchase
import datetime
import jwt
from typing import Optional, List, Dict, Any, Union
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

def get_connection():
    """psycopg2でPostgreSQLへの生接続を取得"""
    return psycopg2.connect(os.environ["DATABASE_URL"])

# データベース接続情報
DB_URL = os.getenv("DATABASE_URL", "sqlite:///shopping_app.db")
JWT_SECRET = os.getenv("JWT_SECRET", "shopping_app_development_secret_key_2025")  # .envから読み込む
ENV = os.getenv("ENV", "development")

# SQLAlchemy エンジンとセッション
engine = None
SessionLocal = None

def init_db():
    """データベース接続を初期化する"""
    global engine, SessionLocal
    
    try:
        # SQLiteの場合は相対パスを絶対パスに変換
        if DB_URL.startswith('sqlite:///'):
            db_path = DB_URL.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                # 相対パスの場合は現在の作業ディレクトリからの絶対パスに変換
                abs_db_path = os.path.join(os.getcwd(), db_path)
                # ディレクトリが存在しない場合は作成
                os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)
                final_db_url = f"sqlite:///{abs_db_path}"
            else:
                final_db_url = DB_URL
        else:
            # PostgreSQLの場合
            final_db_url = DB_URL
            
        logger.info(f"データベース接続URL: {final_db_url} [環境: {ENV}]")
        
        # PostgreSQLエンジン設定
        if final_db_url.startswith('postgresql://'):
            engine = create_engine(
                final_db_url, 
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20,
                echo=False  # デバッグ時はTrueに
            )
            logger.info("PostgreSQL接続を使用します")
        else:
            # SQLiteエンジン設定
            engine = create_engine(
                final_db_url, 
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False  # デバッグ時はTrueに
            )
            logger.info("SQLite接続を使用します")
        
        # セッションファクトリを作成
        SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        
        # テーブル作成（存在しない場合）
        Base.metadata.create_all(bind=engine)
        logger.info("データベース接続を初期化しました")
        
        # PostgreSQL環境の場合、planned_dateカラムが存在しない場合は追加
        if final_db_url.startswith('postgresql://'):
            from sqlalchemy import inspect
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('shopping_list_items')]
            if 'planned_date' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE shopping_list_items ADD COLUMN planned_date DATE;"))
                logger.info("shopping_list_itemsテーブルにplanned_dateカラムを追加しました")
        
        # Railway PostgreSQL使用時のテスト接続
        if final_db_url.startswith('postgresql://'):
            try:
                # 単純なクエリでテスト
                with engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    logger.info(f"Railway PostgreSQL接続テスト成功: {result.fetchone()[0]}")
            except Exception as e:
                logger.error(f"Railway接続テストエラー: {e}")
        
        return True
    except Exception as e:
        logger.error(f"データベース接続エラー: {e}")
        return False

def get_db_health_check() -> Dict[str, Any]:
    """データベース接続の健全性確認"""
    is_pg = DB_URL.startswith('postgresql://')
    db_type = "PostgreSQL" if is_pg else "SQLite"
    
    try:
        if engine is None:
            init_db()
            
        with engine.connect() as connection:
            start_time = datetime.datetime.now()
            result = connection.execute(text("SELECT 1"))
            end_time = datetime.datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
        return {
            "status": "healthy",
            "type": db_type,
            "latency_ms": round(latency_ms, 2),
            "environment": ENV
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "type": db_type,
            "error": str(e),
            "environment": ENV
        }

def get_db_session():
    """データベースセッションを取得"""
    if 'db_session' not in st.session_state:
        if SessionLocal is None:
            init_db()
        st.session_state['db_session'] = SessionLocal()
    
    return st.session_state['db_session']

def close_db_session():
    """データベースセッションをクローズ"""
    if 'db_session' in st.session_state:
        session = st.session_state['db_session']
        try:
            if session.is_active:
                session.rollback()
            session.close()
        except Exception as e:
            import logging
            logging.warning(f"DBセッションのクローズ時に例外: {e}")
        finally:
            del st.session_state['db_session']

# 認証関連の関数
def hash_password(password: str) -> str:
    """パスワードをハッシュ化する"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """パスワードをチェックする"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_id: int) -> str:
    """JWTトークンを作成"""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=14)  # 2週間有効
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[int]:
    """JWTトークンを検証してユーザーIDを取得"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.PyJWTError:
        return None

def logout_user():
    """ログアウト処理。セッション状態はui_utils.pyのlogout関数で処理"""
    # トークン無効化やセッション処理のためのフック（必要に応じて拡張）
    logger.info("ユーザーがログアウトしました")
    return True

# ユーザー関連の関数
def register_user(email: str, password: str, name: str) -> Optional[User]:
    """新規ユーザーを登録"""
    session = get_db_session()
    try:
        # メールアドレスの重複チェック
        existing_user = session.query(User).filter(User.email == email).first()
        if (existing_user):
            return None
            
        # 新規ユーザー作成
        hashed_password = hash_password(password)
        new_user = User(
            email=email,
            password_hash=hashed_password,
            name=name
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception as e:
        logger.error(f"ユーザー登録エラー: {e}")
        session.rollback()
        return None

def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """ユーザーログイン"""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        
        if not user or not check_password(password, user.password_hash):
            return None
            
        # ログイン成功の場合、JWTトークンを生成
        token = create_jwt_token(user.id)
        
        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "token": token
        }
    except Exception as e:
        logger.error(f"ログインエラー: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[User]:
    """ユーザーIDからユーザー情報を取得"""
    session = get_db_session()
    try:
        return session.query(User).filter(User.id == user_id).first()
    except Exception as e:
        logger.error(f"ユーザー取得エラー: {e}")
        return None

# カテゴリ関連の関数
def get_categories(user_id: Optional[int] = None) -> List[Category]:
    """カテゴリ一覧を取得（ユーザー固有 + デフォルト）"""
    session = get_db_session()
    try:
        query = session.query(Category)
        if user_id:
            # ユーザー固有 + ユーザーに紐づかないデフォルトカテゴリ
            query = query.filter((Category.user_id == user_id) | (Category.user_id.is_(None)))
        return query.all()
    except Exception as e:
        logger.error(f"カテゴリ一覧取得エラー: {e}")
        return []

def create_category(name: str, user_id: int) -> Optional[Category]:
    """新しいカテゴリを作成"""
    session = get_db_session()
    try:
        category = Category(
            name=name,
            user_id=user_id
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category
    except Exception as e:
        logger.error(f"カテゴリ作成エラー: {e}")
        session.rollback()
        return None

# 店舗関連の関数
def get_stores(user_id: Optional[int] = None) -> List[Store]:
    """店舗一覧を取得（ユーザー固有 + デフォルト）"""
    session = get_db_session()
    try:
        query = session.query(Store)
        if user_id:
            # ユーザー固有 + ユーザーに紐づかないデフォルト店舗
            query = query.filter((Store.user_id == user_id) | (Store.user_id.is_(None)))
        return query.all()
    except Exception as e:
        logger.error(f"店舗一覧取得エラー: {e}")
        return []

def create_store(user_id, name, category=None, check_duplicate=True):
    """
    新しい店舗を作成する
    
    Args:
        user_id (int): ユーザーID
        name (str): 店舗名
        category (str, optional): カテゴリ
        check_duplicate (bool): 重複チェックを行うかどうか
        
    Returns:
        Store: 作成された店舗オブジェクト、または既存の店舗（重複時）
    """
    from .models import Store
    
    session = get_db_session()
    try:
        # 重複チェック（同じユーザーの同じ名前の店舗を検索）
        if check_duplicate:
            existing_store = session.query(Store).filter(
                Store.user_id == user_id,
                Store.name == name
            ).first()
            
            if existing_store:
                return existing_store
        
        # 新しい店舗を作成
        store = Store(
            user_id=user_id,
            name=name,
            category=category
        )
        session.add(store)
        session.commit()
        return store
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def clean_duplicate_stores(user_id=None):
    """
    重複している店舗を検出して削除する
    同じ名前の店舗が複数ある場合、最も古いものを残して他を削除
    
    Args:
        user_id (int, optional): 特定ユーザーの店舗のみ対象にする場合に指定
    
    Returns:
        dict: 処理結果の情報（削除数、残存数など）
    """
    from sqlalchemy import func
    from .models import Store
    
    session = get_db_session()
    result = {
        "cleaned": 0,
        "remaining": 0,
        "duplicates": {}
    }
    
    try:
        # ユーザーごとに同じ名前の店舗をカウント
        query = session.query(
            Store.name, 
            Store.user_id, 
            func.count(Store.id).label('count')
        ).group_by(
            Store.name, 
            Store.user_id
        ).having(
            func.count(Store.id) > 1
        )
        
        if user_id:
            query = query.filter(Store.user_id == user_id)
        
        duplicate_groups = query.all()
        
        # 重複している店舗ごとに処理
        for name, user_id, count in duplicate_groups:
            # 同じ名前の店舗を取得（IDの昇順）
            stores = session.query(Store).filter(
                Store.name == name,
                Store.user_id == user_id
            ).order_by(Store.id).all()
            
            # 最初の店舗を残し、残りを削除対象にする
            keep_store = stores[0]
            duplicates = stores[1:]
            
            # 重複店舗のIDを記録
            result["duplicates"][name] = {
                "kept_id": keep_store.id,
                "deleted_ids": [s.id for s in duplicates],
                "count": count
            }
            
            # 重複店舗を削除
            for store in duplicates:
                # 関連する買い物リストの店舗IDを更新
                # (この実装は実際のモデル構造に応じて調整が必要)
                session.query(ShoppingListItem).filter(
                    ShoppingListItem.store_id == store.id
                ).update({"store_id": keep_store.id})
                
                # 店舗を削除
                session.delete(store)
                result["cleaned"] += 1
        
        # 残りの店舗数をカウント
        result["remaining"] = session.query(Store).count()
        
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()

# アイテム関連の関数
def get_items_by_user(user_id: int, category_id: Optional[int] = None) -> List[Item]:
    """ユーザーの品目一覧を取得（ユーザー固有 + デフォルト）"""
    session = get_db_session()
    try:
        # ユーザー固有 + ユーザーに紐づかないデフォルトアイテム
        query = session.query(Item).filter((Item.user_id == user_id) | (Item.user_id.is_(None)))
        if category_id:
            query = query.filter(Item.category_id == category_id)
        return query.all()
    except Exception as e:
        logger.error(f"アイテム一覧取得エラー: {e}")
        return []

def create_item(name: str, user_id: int, category_id: Optional[int] = None, default_price: Optional[float] = None) -> Optional[Item]:
    """新しいアイテムを作成"""
    session = get_db_session()
    try:
        item = Item(
            name=name,
            user_id=user_id,
            category_id=category_id,
            default_price=default_price
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item
    except Exception as e:
        logger.error(f"アイテム作成エラー: {e}")
        session.rollback()
        return None

def search_items(user_id: int, query: str) -> List[Item]:
    """品目を名前で検索"""
    session = get_db_session()
    try:
        return session.query(Item)\
            .filter(Item.user_id == user_id)\
            .filter(Item.name.ilike(f'%{query}%'))\
            .all()
    except Exception as e:
        logger.error(f"品目検索エラー: {e}")
        return []

# 買い物リスト関連の関数
def create_shopping_list(user_id: int, date: Optional[datetime.date] = None, memo: Optional[str] = None, name: Optional[str] = None) -> Optional[ShoppingList]:
    """新しい買い物リストを作成"""
    session = get_db_session()
    try:
        shopping_list = ShoppingList(
            user_id=user_id,
            date=date or datetime.date.today(),
            memo=memo,
            name=name or "買い物リスト"
        )
        session.add(shopping_list)
        session.commit()
        session.refresh(shopping_list)
        return shopping_list
    except Exception as e:
        logger.error(f"買い物リスト作成エラー: {e}")
        session.rollback()
        return None

def get_shopping_lists(user_id: int, limit: int = 20) -> List[ShoppingList]:
    """ユーザーの買い物リスト一覧を取得"""
    session = get_db_session()
    try:
        return (
            session.query(ShoppingList)
            .filter(ShoppingList.user_id == user_id)
            .order_by(ShoppingList.date.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        logger.error(f"買い物リスト一覧取得エラー: {e}")
        return []

def get_shopping_list(list_id: int) -> Optional[ShoppingList]:
    """IDから買い物リストを取得"""
    session = get_db_session()
    try:
        return session.query(ShoppingList).filter(ShoppingList.id == list_id).first()
    except Exception as e:
        logger.error(f"買い物リスト取得エラー: {e}")
        return None

def update_shopping_list(list_id: int, name: Optional[str] = None, memo: Optional[str] = None, date: Optional[datetime.date] = None) -> Optional[ShoppingList]:
    """買い物リストを更新"""
    session = get_db_session()
    try:
        shopping_list = session.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        if not shopping_list:
            return None
            
        if name is not None:
            shopping_list.name = name
        if memo is not None:
            shopping_list.memo = memo
        if date is not None:
            shopping_list.date = date
            
        session.commit()
        session.refresh(shopping_list)
        return shopping_list
    except Exception as e:
        logger.error(f"買い物リスト更新エラー: {e}")
        session.rollback()
        return None

# 買い物リストアイテム関連の関数
def add_item_to_shopping_list(
    shopping_list_id: int, 
    item_id: int,
    store_id: Optional[int] = None, 
    planned_price: Optional[float] = None,
    quantity: int = 1
) -> Optional[ShoppingListItem]:
    """買い物リストにアイテムを追加"""
    session = get_db_session()
    try:
        # アイテムがすでにリストに存在するか確認
        existing_item = session.query(ShoppingListItem)\
            .filter(ShoppingListItem.shopping_list_id == shopping_list_id)\
            .filter(ShoppingListItem.item_id == item_id)\
            .filter(ShoppingListItem.store_id == store_id)\
            .first()
            
        if existing_item:
            # すでに存在する場合は数量を更新
            existing_item.quantity += quantity
            if planned_price is not None:
                existing_item.planned_price = planned_price
            session.commit()
            session.refresh(existing_item)
            return existing_item
            
        # 新規アイテムの場合
        list_item = ShoppingListItem(
            shopping_list_id=shopping_list_id,
            item_id=item_id,
            store_id=store_id,
            planned_price=planned_price,
            quantity=quantity,
            checked=False
        )
        session.add(list_item)
        session.commit()
        session.refresh(list_item)
        return list_item
    except Exception as e:
        logger.error(f"アイテム追加エラー: {e}")
        session.rollback()
        return None

def get_shopping_list_items(shopping_list_id: int, store_id: Optional[int] = None) -> List[ShoppingListItem]:
    """買い物リスト内のアイテム一覧を取得"""
    session = get_db_session()
    try:
        query = session.query(ShoppingListItem)\
            .filter(ShoppingListItem.shopping_list_id == shopping_list_id)
            
        if store_id:
            query = query.filter(ShoppingListItem.store_id == store_id)
            
        return query.all()
    except Exception as e:
        logger.error(f"買い物リストアイテム取得エラー: {e}")
        return []
    finally:
        if session != st.session_state.get('db_session'):
            session.close()

# 買い物リスト全体の合計金額とアイテム数を計算
def get_shopping_list_total(shopping_list_id: int) -> dict:
    """
    買い物リストの合計金額と商品数を計算する

    Args:
        shopping_list_id (int): 買い物リストのID

    Returns:
        dict: {"total_price": 合計予定金額, "total_items": アイテム数, "checked_items": 購入済み数, "checked_price": 購入済み金額合計}
    """
    session = get_db_session()
    try:
        items = get_shopping_list_items(shopping_list_id)
        total_price = sum((item.planned_price or 0) * item.quantity for item in items)
        total_items = len(items)
        checked_items = sum(1 for item in items if item.checked)
        checked_price = sum((item.planned_price or 0) * item.quantity for item in items if item.checked)
        return {
            "total_price": total_price,
            "total_items": total_items,
            "checked_items": checked_items,
            "checked_price": checked_price
        }
    except Exception as e:
        logger.error(f"買い物リスト合計金額計算エラー: {e}")
        return {"total_price": 0, "total_items": 0, "checked_items": 0, "checked_price": 0}
    finally:
        if session != st.session_state.get('db_session'):
            session.close()

def update_shopping_list_item(
    item_id: int,
    checked: Optional[bool] = None,
    quantity: Optional[int] = None,
    store_id: Optional[int] = None,
    planned_price: Optional[float] = None,
    planned_date: Optional[datetime.date] = None
) -> Optional[ShoppingListItem]:
    """買い物リストアイテムを更新（チェック状態、数量、店舗、価格、予定日）"""
    # 新規セッションを使用
    session = SessionLocal()
    try:
        list_item = session.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
        if not list_item:
            return None
        
        if checked is not None:
            list_item.checked = checked
        if quantity is not None:
            list_item.quantity = quantity
        if store_id is not None:
            list_item.store_id = store_id
        if planned_price is not None:
            list_item.planned_price = planned_price
        if planned_date is not None:
            list_item.planned_date = planned_date
        
        session.commit()
        session.refresh(list_item)
        return list_item
    except Exception as e:
        logger.error(f"買い物リストアイテム更新エラー: {e}")
        session.rollback()
        return None
    finally:
        session.close()

def delete_shopping_list_item(item_id: int) -> bool:
    """買い物リストからアイテムを削除"""
    session = get_db_session()
    try:
        list_item = session.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
        if not list_item:
            return False
            
        session.delete(list_item)
        session.commit()
        return True
    except Exception as e:
        logger.error(f"買い物リストアイテム削除エラー: {e}")
        session.rollback()
        return False

def remove_item_from_shopping_list(item_id: int) -> bool:
    """ショッピングリストから特定のアイテムを削除する

    Args:
        item_id (int): 削除するショッピングリストアイテムのID

    Returns:
        bool: 削除に成功した場合はTrue、失敗した場合はFalse
    """
    if not item_id:
        return False
    
    try:
        session = SessionLocal()
        item = session.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
        
        if not item:
            return False
        
        session.delete(item)
        session.commit()
        return True
    except Exception as e:
        logger.error(f"ショッピングリストアイテムの削除エラー: {e}")
        return False
    finally:
        session.close()

def delete_shopping_list_items(item_ids: List[int]) -> bool:
    """複数のショッピングリストアイテムを一括削除する

    Args:
        item_ids (List[int]): 削除するショッピングリストアイテムのIDリスト

    Returns:
        bool: 削除に成功した場合はTrue、失敗した場合はFalse
    """
    if not item_ids:
        return False
    
    try:
        session = SessionLocal()
        
        # 一括削除を実行
        for item_id in item_ids:
            item = session.query(ShoppingListItem).filter(ShoppingListItem.id == item_id).first()
            if item:
                session.delete(item)
        
        session.commit()
        return True
    except Exception as e:
        logger.error(f"ショッピングリストアイテムの一括削除エラー: {e}")
        session.rollback()
        return False
    finally:
        session.close()

# 購入履歴関連の関数
def record_purchase(
    shopping_list_item_id: int,
    actual_price: float,
    quantity: Optional[int] = None
) -> Optional[Purchase]:
    """購入履歴を記録"""
    session = get_db_session()
    try:
        # 対象アイテムの取得
        list_item = session.query(ShoppingListItem).filter(ShoppingListItem.id == shopping_list_item_id).first()
        if not list_item:
            return None
        
        # 購入数が指定されていない場合はリストアイテムの数量を使用
        if quantity is None:
            quantity = list_item.quantity
        
        # 購入履歴を記録
        purchase = Purchase(
            shopping_list_item_id=shopping_list_item_id,
            actual_price=actual_price,
            quantity=quantity
        )
        
        # アイテムをチェック済みに
        list_item.checked = True
        
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase
    except Exception as e:
        logger.error(f"購入履歴記録エラー: {e}")
        session.rollback()
        return None

def get_purchase_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーの購入履歴を取得"""
    session = get_db_session()
    try:
        # 購入履歴を取得するSQLクエリ
        query = text("""
        SELECT 
            p.id,
            p.actual_price,
            p.quantity,
            p.purchased_at,
            i.name as item_name,
            c.name as category_name,
            s.name as store_name,
            sl.date as shopping_date
        FROM 
            purchases p
        JOIN 
            shopping_list_items sli ON p.shopping_list_item_id = sli.id
        JOIN 
            shopping_lists sl ON sli.shopping_list_id = sl.id
        LEFT JOIN 
            items i ON sli.item_id = i.id
        LEFT JOIN 
            categories c ON i.category_id = c.id
        LEFT JOIN 
            stores s ON sli.store_id = s.id
        WHERE 
            sl.user_id = :user_id
        ORDER BY 
            p.purchased_at DESC
        LIMIT :limit
        """)
        
        result = session.execute(query, {"user_id": user_id, "limit": limit})
        
        # 結果を辞書のリストに変換
        purchases = []
        for row in result:
            purchases.append({
                "id": row.id,
                "actual_price": float(row.actual_price),
                "quantity": row.quantity,
                "purchased_at": row.purchased_at,
                "item_name": row.item_name,
                "category_name": row.category_name or "未分類",
                "store_name": row.store_name,
                "shopping_date": row.shopping_date
            })
            
        return purchases
    except Exception as e:
        logger.error(f"購入履歴取得エラー: {e}")
        return []

# 支出集計関連の関数
def get_monthly_spending(user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
    """月ごとの支出サマリーを取得"""
    session = get_db_session()
    try:
        # 指定した年月の範囲を計算
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)
            
        # SQL実行
        query = text("""
        SELECT 
            c.name as category,
            SUM(p.actual_price * p.quantity) as total_spending
        FROM 
            purchases p
        JOIN 
            shopping_list_items sli ON p.shopping_list_item_id = sli.id
        JOIN 
            shopping_lists sl ON sli.shopping_list_id = sl.id
        LEFT JOIN 
            items i ON sli.item_id = i.id
        LEFT JOIN 
            categories c ON i.category_id = c.id
        WHERE 
            sl.user_id = :user_id
            AND DATE(p.purchased_at) >= :start_date
            AND DATE(p.purchased_at) < :end_date
        GROUP BY 
            c.name
        """)
        
        result = session.execute(query, {"user_id": user_id, "start_date": start_date, "end_date": end_date})
        
        # 結果を辞書のリストに変換
        spending_data = []
        for row in result:
            spending_data.append({
                "category": row.category or "未分類",
                "total_spending": float(row.total_spending)
            })
            
        return spending_data
    except Exception as e:
        logger.error(f"月次支出取得エラー: {e}")
        return []

def get_user_purchases(user_id: int, start_date: Optional[datetime.datetime] = None, end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """ユーザーの購入履歴を取得"""
    session = get_db_session()
    try:
        # 購入履歴を取得するSQLクエリ
        query = text("""
        SELECT 
            p.id,
            p.actual_price,
            p.quantity,
            p.purchased_at,
            i.name as item_name,
            c.name as category_name,
            s.name as store_name,
            sl.date as shopping_date
        FROM 
            purchases p
        JOIN 
            shopping_list_items sli ON p.shopping_list_item_id = sli.id
        JOIN 
            shopping_lists sl ON sli.shopping_list_id = sl.id
        JOIN 
            items i ON sli.item_id = i.id
        LEFT JOIN 
            categories c ON i.category_id = c.id
        LEFT JOIN 
            stores s ON sli.store_id = s.id
        WHERE 
            sl.user_id = :user_id
        """
        )
        
        # 日付範囲フィルタを追加
        params = {"user_id": user_id}
        if start_date:
            query = text(query.text + " AND p.purchased_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(query.text + " AND p.purchased_at <= :end_date")
            params["end_date"] = end_date
            
        # 日付順でソート
        query = text(query.text + " ORDER BY p.purchased_at DESC")
        
        result = session.execute(query, params)
        
        # 結果を辞書のリストに変換
        purchases = []
        for row in result:
            purchases.append({
                "id": row.id,
                "actual_price": float(row.actual_price),
                "quantity": row.quantity,
                "purchased_at": row.purchased_at,
                "item_name": row.item_name,
                "category_name": row.category_name or "未分類",
                "store_name": row.store_name or "未設定",
                "shopping_date": row.shopping_date,
                "total": float(row.actual_price) * row.quantity
            })
            
        return purchases
    except Exception as e:
        logger.error(f"購入履歴取得エラー: {e}")
        return []

def get_category_spending(user_id: int, start_date: Optional[datetime.datetime] = None, end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """カテゴリ別支出を集計"""
    session = get_db_session()
    try:
        # カテゴリ別に支出を集計するSQLクエリ
        query = text("""
        SELECT 
            COALESCE(c.name, '未分類') as category,
            SUM(p.actual_price * p.quantity) as total_amount
        FROM 
            purchases p
        JOIN 
            shopping_list_items sli ON p.shopping_list_item_id = sli.id
        JOIN 
            shopping_lists sl ON sli.shopping_list_id = sl.id
        JOIN 
            items i ON sli.item_id = i.id
        LEFT JOIN 
            categories c ON i.category_id = c.id
        WHERE 
            sl.user_id = :user_id
        """
        )
        
        # 日付範囲フィルタを追加
        params = {"user_id": user_id}
        if start_date:
            query = text(query.text + " AND p.purchased_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(query.text + " AND p.purchased_at <= :end_date")
            params["end_date"] = end_date
            
        # カテゴリでグループ化
        query = text(query.text + " GROUP BY COALESCE(c.name, '未分類') ORDER BY total_amount DESC")
        
        result = session.execute(query, params)
        
        # 結果を辞書のリストに変換
        category_spending = []
        for row in result:
            category_spending.append({
                "category": row.category,
                "total_spending": float(row.total_amount)
            })
            
        return category_spending
    except Exception as e:
        logger.error(f"カテゴリ別支出集計エラー: {e}")
        return []

def get_store_spending(user_id: int, start_date: Optional[datetime.datetime] = None, end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """店舗別支出を集計"""
    session = get_db_session()
    try:
        # 店舗別に支出を集計するSQLクエリ
        query = text("""
        SELECT 
            COALESCE(s.name, '未設定') as store,
            SUM(p.actual_price * p.quantity) as total_amount
        FROM 
            purchases p
        JOIN 
            shopping_list_items sli ON p.shopping_list_item_id = sli.id
        JOIN 
            shopping_lists sl ON sli.shopping_list_id = sl.id
        LEFT JOIN 
            stores s ON sli.store_id = s.id
        WHERE 
            sl.user_id = :user_id
        """
        )
        
        # 日付範囲フィルタを追加
        params = {"user_id": user_id}
        if start_date:
            query = text(query.text + " AND p.purchased_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(query.text + " AND p.purchased_at <= :end_date")
            params["end_date"] = end_date
            
        # 店舗でグループ化
        query = text(query.text + " GROUP BY COALESCE(s.name, '未設定') ORDER BY total_amount DESC")
        
        result = session.execute(query, params)
        
        # 結果を辞書のリストに変換
        store_spending = []
        for row in result:
            store_spending.append({
                "store": row.store,
                "total_spending": float(row.total_amount)
            })
            
        return store_spending
    except Exception as e:
        logger.error(f"店舗別支出集計エラー: {e}")
        return []

def save_purchase(
    user_id: int,
    item_id: int,
    store_id: int,
    quantity: int,
    price: float,
    purchase_date: Optional[datetime.date] = None,
    note: Optional[str] = None
) -> Optional[Purchase]:
    """購入履歴を保存"""
    session = get_db_session()
    try:
        purchase = Purchase(
            user_id=user_id,
            item_id=item_id,
            store_id=store_id,
            quantity=quantity,
            price=price,
            purchase_date=purchase_date or datetime.date.today(),
            note=note
        )
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase
    except Exception as e:
        logger.error(f"購入履歴保存エラー: {e}")
        session.rollback()
        return None

def update_purchase_date(purchase_id: int, new_date: datetime.datetime) -> bool:
    """購入履歴の日付（purchased_at）を更新する"""
    session = get_db_session()
    try:
        purchase = session.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            return False
        purchase.purchased_at = new_date
        session.commit()
        return True
    except Exception as e:
        logger.error(f"購入日付更新エラー: {e}")
        session.rollback()
        return False

def get_latest_planned_price(user_id: int, item_id: int) -> Optional[float]:
    """指定ユーザー・商品IDの直近のplanned_priceを取得"""
    session = get_db_session()
    try:
        item = (
            session.query(ShoppingListItem)
            .join(ShoppingList, ShoppingListItem.shopping_list_id == ShoppingList.id)
            .filter(ShoppingList.user_id == user_id)
            .filter(ShoppingListItem.item_id == item_id)
            .order_by(ShoppingListItem.created_at.desc())
            .first()
        )
        if item and item.planned_price is not None:
            return float(item.planned_price)
        return None
    except Exception as e:
        logger.error(f"直近予定金額取得エラー: {e}")
        return None

# データベース初期化を実行
init_db()