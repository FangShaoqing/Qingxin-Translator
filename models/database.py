"""
Qingxin Translator - Database
数据库初始化与管理
"""

from peewee import SqliteDatabase, Model
from pathlib import Path

from app.constants import DATABASE_FILE, DATA_DIR

# 数据库实例
db = SqliteDatabase(None)


class BaseModel(Model):
    """基础模型类"""
    class Meta:
        database = db


def init_db(db_path: Path = None) -> None:
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径，默认使用 DATABASE_FILE
    """
    if db_path is None:
        db_path = DATABASE_FILE
    
    # 确保数据目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 初始化数据库连接
    db.init(str(db_path))
    db.connect()
    
    # 导入模型以确保表被创建
    from models.history import History
    from models.favorite import Favorite, FavoriteGroup
    
    # 创建表
    db.create_tables([History, Favorite, FavoriteGroup], safe=True)
    
    print(f"Database initialized: {db_path}")


def close_db() -> None:
    """关闭数据库连接"""
    if not db.is_closed():
        db.close()
        print("Database connection closed")


def get_db() -> SqliteDatabase:
    """获取数据库实例"""
    return db
