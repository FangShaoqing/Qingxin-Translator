"""
Qingxin Translator - PyInstaller Configuration
打包配置文件
"""

import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path('.').resolve()

# PyInstaller配置
config = {
    # 主程序入口
    'script': 'main.py',
    
    # 程序名称
    'name': 'QingxinTranslator',
    
    # 打包成单文件（--onefile）
    'onefile': True,
    
    # 是否显示控制台（调试时设为True）
    'console': False,
    
    # 应用图标
    'icon': str(ROOT_DIR / 'resources' / 'icons' / 'app.ico'),
    
    # 需要包含的数据文件
    'datas': [
        (str(ROOT_DIR / 'resources' / 'icons'), 'resources/icons'),
        (str(ROOT_DIR / 'web'), 'web'),
        (str(ROOT_DIR / 'core' / 'ocr.ps1'), 'core'),  # Windows OCR 脚本（图片翻译依赖）
    ],
    
    # 需要包含的隐藏导入
    'hiddenimports': [
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'langdetect',
        'peewee',
        'httpx',
        'pystray',
        'pystray._win32',
    ],
    
    # 排除的模块（减小体积）
    'excludes': [
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtSvg',
    ],
}


def get_pyinstaller_args():
    """获取PyInstaller命令行参数"""
    args = [
        config['script'],
        '--name', config['name'],
        '--icon', config['icon'],
    ]
    
    if not config['onefile']:
        args.append('--onedir')
    else:
        args.append('--onefile')
    
    if not config['console']:
        args.append('--windowed')
    
    # 添加数据文件
    for src, dst in config['datas']:
        args.extend(['--add-data', f'{src};{dst}'])
    
    # 添加隐藏导入
    for module in config['hiddenimports']:
        args.extend(['--hidden-import', module])
    
    # 排除模块
    for module in config['excludes']:
        args.extend(['--exclude-module', module])
    
    return args


if __name__ == '__main__':
    import PyInstaller.__main__
    
    args = get_pyinstaller_args()
    print(f"PyInstaller args: {args}")
    
    PyInstaller.__main__.run(args)
