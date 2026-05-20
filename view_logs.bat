@echo off
REM ============================================================
REM 后端日志查看脚本
REM 使用方法:
REM   1. 直接运行: 查看当前终端日志
REM   2. 查看文件日志: 如果配置了日志文件
REM ============================================================

echo ==========================================
echo    后端日志查看工具
echo ==========================================
echo.
echo 可用的日志查看方式:
echo   [1] 查看运行中的后端服务器日志
echo   [2] 查看日志文件（如果有）
echo   [3] 显示帮助
echo.
set /p choice="请选择 (1/2/3): "

if "%choice%"=="1" goto view_terminal
if "%choice%"=="2" goto view_file
if "%choice%"=="3" goto help

goto end

:view_terminal
echo.
echo 提示: 在 Trae 中查看终端 6 的实时日志即可！
echo.
echo ==========================================
echo    后端服务器状态
echo ==========================================
echo 终端 ID: 6
echo 服务地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
echo ==========================================
echo    最近日志（手动查看）
echo ==========================================
echo 你可以:
echo   1. 在 Trae 的终端面板查看终端 6 的输出
echo   2. 或者我可以帮你用 CheckCommandStatus 查看最新日志
echo.
pause
goto end

:view_file
echo.
echo ==========================================
echo    检查日志文件
echo ==========================================
echo.

REM 检查是否有 logs 目录
if exist "logs\" (
    echo 找到 logs 目录
    echo.
    dir /b logs\*.log 2>nul
    if %errorlevel%==0 (
        echo.
        echo 按任意键查看最新的日志文件...
        pause >nul
        for /f "delims=" %%f in ('dir /b /o-d logs\*.log 2^>nul') do (
            if not defined LOG_FILE set "LOG_FILE=%%f"
        )
        if defined LOG_FILE (
            echo.
            echo 正在查看: logs\%LOG_FILE%
            echo ==========================================
            type "logs\%LOG_FILE%"
        )
    ) else (
        echo 未找到日志文件
    )
) else (
    echo logs 目录不存在
    echo 提示: 当前日志只输出到终端
    echo.
    echo 如需配置日志文件，请在 backend/core/config.py 中添加日志配置
)
echo.
pause
goto end

:help
echo.
echo ==========================================
echo    帮助文档
echo ==========================================
echo.
echo 1. 实时日志查看
echo    在 Trae IDE 的终端面板，找到终端 6（后端服务器）
echo    就可以看到实时输出的日志
echo.
echo 2. 关键日志类型
echo    - INFO:    正常信息
echo    - WARNING: 警告信息
echo    - ERROR:   错误信息
echo.
echo 3. 有用的日志关键字
echo    - "【模拟发送短信】": 找到验证码
echo    - "验证码发送成功": 查看发送的验证码
echo    - "POST /api/auth/sms/send": 查看发送验证码的请求
echo.
echo 4. 如果需要配置文件日志
echo    可以在 backend/core/config.py 中添加日志文件配置
echo.
pause
goto end

:end
