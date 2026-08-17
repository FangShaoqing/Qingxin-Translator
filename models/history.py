"""
Qingxin Translator - History Model
翻译历史记录模型
"""

import datetime
from typing import List, Optional

from peewee import TextField, DateTimeField, CharField, IntegerField

from models.database import BaseModel, db


class History(BaseModel):
    """
    翻译历史记录模型
    """
    source_text = TextField(verbose_name="原文")
    translated_text = TextField(verbose_name="译文")
    source_lang = CharField(max_length=10, verbose_name="源语言")
    target_lang = CharField(max_length=10, verbose_name="目标语言")
    engine = CharField(max_length=20, verbose_name="翻译引擎")
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    
    class Meta:
        table_name = "history"
        order_by = ("-created_at",)
    
    @classmethod
    def add(cls, source_text: str, translated_text: str, 
            source_lang: str, target_lang: str, engine: str) -> "History":
        """
        添加翻译记录
        
        Args:
            source_text: 原文
            translated_text: 译文
            source_lang: 源语言
            target_lang: 目标语言
            engine: 翻译引擎
            
        Returns:
            新创建的历史记录
        """
        return cls.create(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            engine=engine
        )
    
    @classmethod
    def search(cls, keyword: str, limit: int = 50) -> List["History"]:
        """
        搜索历史记录
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的历史记录列表
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
    def get_recent(cls, limit: int = 100) -> List["History"]:
        """
        获取最近的翻译记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最近的历史记录列表（倒序）
        """
        return cls.select().order_by(cls.created_at.desc()).limit(limit)
    
    @classmethod
    def delete_by_id(cls, record_id: int) -> bool:
        """
        根据ID删除记录
        
        Args:
            record_id: 记录ID
            
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
    def clear_all(cls) -> int:
        """
        清空所有历史记录
        
        Returns:
            删除的记录数量
        """
        count = cls.select().count()
        cls.delete().execute()
        return count
    
    @classmethod
    def get_count(cls) -> int:
        """获取记录总数"""
        return cls.select().count()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "engine": self.engine,
            "created_at": self.created_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"History(id={self.id}, source='{self.source_text[:20]}...', engine='{self.engine}')"
