"""
Qingxin Translator - PyInstaller Configuration
打包配置文件

用法：
    python build.py                     # 默认 onefile（便携单文件，根目录发布用）
    python build.py --mode onedir       # onedir（目录模式，启动快，安装版用）
"""

import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path('.').resolve()

# 打包模式：onefile（单文件） / onedir（目录）
MODE = "onefile"
if "--mode" in sys.argv:
    idx = sys.argv.index("--mode")
    if idx + 1 < len(sys.argv):
        MODE = sys.argv[idx + 1].lower()
        if MODE not in ("onefile", "onedir"):
            print(f"Unknown mode: {MODE}, use onefile or onedir")
            sys.exit(1)

# PyInstaller配置
config = {
    # 主程序入口
    'script': 'main.py',
    
    # 程序名称
    'name': 'QingxinTranslator',
    
    # 打包模式（onefile 单文件 / onedir 目录）
    'onefile': MODE == "onefile",
    
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
    print(f"PyInstaller args (mode={MODE}): {args}")
    
    PyInstaller.__main__.run(args)
