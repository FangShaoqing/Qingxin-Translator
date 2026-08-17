"""
Qingxin Translator - Favorite Model
收藏夹模型
"""

import datetime
from typing import List, Optional

from peewee import TextField, DateTimeField, CharField, ForeignKeyField

from models.database import BaseModel, db


class FavoriteGroup(BaseModel):
    """
    收藏分组模型
    """
    name = CharField(max_length=100, verbose_name="分组名称")
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    
    class Meta:
        table_name = "favorite_group"
        order_by = ("name",)
    
    @classmethod
    def create_group(cls, name: str) -> "FavoriteGroup":
        """
        创建新分组
        
        Args:
            name: 分组名称
            
        Returns:
            新创建的分组
        """
        return cls.create(name=name)
    
    @classmethod
    def get_or_create_default(cls) -> "FavoriteGroup":
        """获取或创建默认分组"""
        group, created = cls.get_or_create(name="默认分组")
        return group
    
    @classmethod
    def get_all_groups(cls) -> List["FavoriteGroup"]:
        """获取所有分组"""
        return list(cls.select())
    
    @classmethod
    def delete_group(cls, group_id: int) -> bool:
        """
        删除分组（同时删除分组下的收藏）
        
        Args:
            group_id: 分组ID
            
        Returns:
            是否删除成功
        """
        try:
            group = cls.get(cls.id == group_id)
            # 删除分组下的所有收藏
            Favorite.delete().where(Favorite.group == group).execute()
            group.delete_instance()
            return True
        except cls.DoesNotExist:
            return False
    
    def get_favorites(self) -> List["Favorite"]:
        """获取该分组下的所有收藏"""
        return list(Favorite.select().where(Favorite.group == self))
    
    def get_favorite_count(self) -> int:
        """获取该分组下的收藏数量"""
        return Favorite.select().where(Favorite.group == self).count()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "count": self.get_favorite_count(),
        }
    
    def __repr__(self) -> str:
        return f"FavoriteGroup(id={self.id}, name='{self.name}')"


class Favorite(BaseModel):
    """
    收藏记录模型
    """
    source_text = TextField(verbose_name="原文")
    translated_text = TextField(verbose_name="译文")
    source_lang = CharField(max_length=10, verbose_name="源语言")
    target_lang = CharField(max_length=10, verbose_name="目标语言")
    group = ForeignKeyField(FavoriteGroup, backref="favorites", verbose_name="所属分组")
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    
    class Meta:
        table_name = "favorite"
        order_by = ("-created_at",)
    
    @classmethod
    def add(cls, source_text: str, translated_text: str,
            source_lang: str, target_lang: str, 
            group: Optional[FavoriteGroup] = None) -> "Favorite":
        """
        添加收藏
        
        Args:
            source_text: 原文
            translated_text: 译文
            source_lang: 源语言
            target_lang: 目标语言
            group: 所属分组，默认使用默认分组
            
        Returns:
            新创建的收藏记录
        """
        if group is None:
            group = FavoriteGroup.get_or_create_default()
        
        return cls.create(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            group=group
        )
    
    @classmethod
    def is_favorited(cls, source_text: str) -> bool:
        """
        检查是否已收藏
        
        Args:
            source_text: 原文
            
        Returns:
            是否已收藏
        """
        return cls.select().where(cls.source_text == source_text).exists()
    
    @classmethod
    def search(cls, keyword: str, limit: int = 50) -> List["Favorite"]:
        """
        搜索收藏
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的收藏列表
        """
        return (
            cls.select()
            .where(
                (cls.source_text.contains(keyword)) |
                (cls.translated_text.contains(keyword))
            )
            .limit(limit)
        )
    
    @classmethod
    def get_by_group(cls, group: FavoriteGroup) -> List["Favorite"]:
        """获取指定分组的收藏"""
        return list(cls.select().where(cls.group == group))
    
    @classmethod
    def delete_by_id(cls, record_id: int) -> bool:
        """
        根据ID删除收藏
        
        Args:
            record_id: 收藏ID
            
        Returns:
            是否删除成功
        """
        try:
            record = cls.get(cls.id == record_id)
            record.delete_instance()
            return True
        except cls.DoesNotExist:
            return False
    
    @classmethod
    def toggle(cls, source_text: str, translated_text: str,
               source_lang: str, target_lang: str,
               group: Optional[FavoriteGroup] = None) -> bool:
        """
        切换收藏状态
        
        Args:
            source_text: 原文
            translated_text: 译文
            source_lang: 源语言
            target_lang: 目标语言
            group: 所属分组
            
        Returns:
            切换后的收藏状态（True表示已收藏）
        """
        if cls.is_favorited(source_text):
            # 取消收藏
            cls.delete().where(cls.source_text == source_text).execute()
            return False
        else:
            # 添加收藏
            cls.add(source_text, translated_text, source_lang, target_lang, group)
            return True
    
    @classmethod
    def get_count(cls) -> int:
        """获取收藏总数"""
        return cls.select().count()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "group_id": self.group_id,
            "group_name": self.group.name,
            "created_at": self.created_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"Favorite(id={self.id}, source='{self.source_text[:20]}...', group='{self.group.name}')"
