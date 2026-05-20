@echo off
REM 安装前端依赖
echo 正在安装前端依赖...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo 安装失败！
    pause
    exit /b 1
)
echo.
echo 依赖安装完成！
echo.
echo 请重启前端开发服务器
pause
