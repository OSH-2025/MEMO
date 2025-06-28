@echo off
chcp 65001 >nul
title 活动预测客户端

echo.
echo 启动活动预测客户端...
echo 连接服务器: js1.blockelite.cn:8888
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python未安装或未添加到PATH
    echo 请先安装Python并添加到系统PATH
    pause
    exit /b 1
)

REM 检查pip是否可用
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误: pip不可用
    pause
    exit /b 1
)

echo Python环境检查通过

REM 安装必要的依赖
echo.
echo 检查并安装Python依赖...
pip install requests psutil pywin32 pygetwindow >nul 2>&1
if errorlevel 1 (
    echo 警告: 依赖安装失败，尝试继续运行...
) else (
    echo 依赖安装完成
)

echo.
echo 测试服务器连接...
python -c "import requests; r=requests.get('http://js1.blockelite.cn:8888/health', timeout=5); print('服务器连接正常' if r.status_code==200 else '服务器响应异常')" 2>nul
if errorlevel 1 (
    echo 错误: 无法连接到服务器 js1.blockelite.cn:8888
    echo 请检查:
    echo   1. 网络连接是否正常
    echo   2. 服务器是否已启动
    echo   3. 防火墙是否阻止连接
    echo.
    echo 是否继续尝试启动客户端？
    set /p choice=请输入 y/n: 
    if /i not "%choice%"=="y" exit /b 1
)

echo.
echo 启动选项:
echo   1. 演示模式 (使用模拟数据)
echo   2. 实时监控模式 (监控真实活动)
echo   3. 测试连接模式
echo.
set /p mode=请选择模式 (1-3): 

if "%mode%"=="1" (
    echo.
    echo 启动演示模式...
    python windows_client.py --demo --server js1.blockelite.cn:8888
) else if "%mode%"=="2" (
    echo.
    echo 启动实时监控模式...
    echo 警告: 此模式将监控您的窗口活动并发送到服务器
    echo 按 Ctrl+C 停止监控
    python windows_client.py -c configs/client_config.json
) else if "%mode%"=="3" (
    echo.
    echo 测试连接模式...
    python windows_client.py --test --server js1.blockelite.cn:8888
) else (
    echo 无效选择，启动默认演示模式...
    python windows_client.py --demo --server js1.blockelite.cn:8888
)

echo.
echo 客户端已结束运行
echo 提示:
echo   - 查看服务器状态: http://js1.blockelite.cn:8888/health
echo   - 重新启动: 双击 start_client_safe.bat
echo.
pause 