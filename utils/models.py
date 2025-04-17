from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Text, Numeric, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import uuid

Base = declarative_base()

class User(Base):
    """ユーザー情報モデル"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    shopping_lists = relationship("ShoppingList", back_populates="user", cascade="all, delete-orphan")
    stores = relationship("Store", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="user", cascade="all, delete-orphan")

class Store(Base):
    """店舗モデル"""
    __tablename__ = 'stores'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    user = relationship("User", back_populates="stores")
    shopping_list_items = relationship("ShoppingListItem", back_populates="store")

class Category(Base):
    """カテゴリモデル"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    user = relationship("User", back_populates="categories")
    items = relationship("Item", back_populates="category")
    
    def __str__(self):
        return self.name

class Item(Base):
    """商品アイテムモデル"""
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    default_price = Column(Numeric)
    category_id = Column(Integer, ForeignKey('categories.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    category = relationship("Category", back_populates="items")
    user = relationship("User", back_populates="items")
    shopping_list_items = relationship("ShoppingListItem", back_populates="item")

class ShoppingList(Base):
    """買い物リストモデル"""
    __tablename__ = 'shopping_lists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(Date, default=datetime.date.today)
    name = Column(String, default="買い物リスト")  # 名前フィールドを追加
    memo = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    user = relationship("User", back_populates="shopping_lists")
    shopping_list_items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")

class ShoppingListItem(Base):
    """買い物リスト内アイテムモデル"""
    __tablename__ = 'shopping_list_items'

    id = Column(Integer, primary_key=True)
    shopping_list_id = Column(Integer, ForeignKey('shopping_lists.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'))
    store_id = Column(Integer, ForeignKey('stores.id'))
    planned_price = Column(Numeric)
    checked = Column(Boolean, default=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    shopping_list = relationship("ShoppingList", back_populates="shopping_list_items")
    item = relationship("Item", back_populates="shopping_list_items")
    store = relationship("Store", back_populates="shopping_list_items")
    purchases = relationship("Purchase", back_populates="shopping_list_item", cascade="all, delete-orphan")

class Purchase(Base):
    """購入履歴モデル"""
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True)
    shopping_list_item_id = Column(Integer, ForeignKey('shopping_list_items.id'), nullable=False)
    actual_price = Column(Numeric, nullable=False)
    quantity = Column(Integer, nullable=False)
    purchased_at = Column(DateTime, default=datetime.datetime.utcnow)

    # リレーションシップ
    shopping_list_item = relationship("ShoppingListItem", back_populates="purchases")