"""
Qingxin Translator - Logger
日志记录模块
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


# 日志目录（使用 constants 中的 DATA_DIR，自动适配打包环境）
from app.constants import DATA_DIR
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件路径
LOG_FILE = LOG_DIR / "app.log"


class Logger:
    """日志管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._logger = logging.getLogger("QingxinTranslator")
        self._logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self._logger.handlers:
            self._setup_handlers()
        
        self._initialized = True
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器（简洁格式）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        
        # 文件处理器（详细格式，自动轮转）
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)
    
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)
    
    def get_log_file(self):
        """获取日志文件路径"""
        return LOG_FILE


# 全局日志器
log = Logger()


# 导出
__all__ = ["log", "Logger"]
