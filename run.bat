@echo off
chcp 65001 >nul
echo ========================================
echo   青欣翻译 - 启动脚本
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查依赖
echo 检查依赖...
pip show pywebview >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装pywebview...
    pip install pywebview
)

echo.
echo 启动应用...
echo.

python main.py

pause
