@echo off
REM ==========================================
REM 自签名SSL证书生成脚本 (Windows)
REM 用于开发和测试环境
REM ==========================================

setlocal enabledelayedexpansion

echo ==========================================
echo 自签名SSL证书生成工具
echo ==========================================
echo.

REM 设置证书目录
set CERT_DIR=%~dp0..\ssl
if not exist "%CERT_DIR%" mkdir "%CERT_DIR%"

REM 设置证书信息
set DOMAIN=localhost
set COUNTRY=CN
set STATE=Shanghai
set LOCALITY=Shanghai
set ORGANIZATION=SushiDigitalHuman
set ORGANIZATIONAL_UNIT=Dev
set EMAIL=dev@sushidigital.com

echo 正在生成自签名SSL证书...
echo.
echo 证书信息:
echo   域名: %DOMAIN%
echo   国家: %COUNTRY%
echo   省份: %STATE%
echo   城市: %LOCALITY%
echo   组织: %ORGANIZATION%
echo   部门: %ORGANIZATIONAL_UNIT%
echo   邮箱: %EMAIL%
echo.

REM 检查OpenSSL是否可用
where openssl >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到OpenSSL！
    echo.
    echo 请安装OpenSSL:
    echo 1. 下载: https://slproweb.com/products/Win32OpenSSL.html
    echo 2. 或将Git Bash中的openssl添加到PATH
    echo.
    pause
    exit /b 1
)

echo [1/3] 生成私钥...
openssl genrsa -out "%CERT_DIR%\privkey.pem" 2048
if %errorlevel% neq 0 (
    echo [错误] 私钥生成失败！
    pause
    exit /b 1
)

echo [2/3] 生成证书签名请求...
openssl req -new -key "%CERT_DIR%\privkey.pem" -out "%CERT_DIR%\csr.pem" -subj "/C=%COUNTRY%/ST=%STATE%/L=%LOCALITY%/O=%ORGANIZATION%/OU=%ORGANIZATIONAL_UNIT%/CN=%DOMAIN%/emailAddress=%EMAIL%"
if %errorlevel% neq 0 (
    echo [错误] CSR生成失败！
    pause
    exit /b 1
)

echo [3/3] 生成自签名证书（有效期365天）...
openssl x509 -req -days 365 -in "%CERT_DIR%\csr.pem" -signkey "%CERT_DIR%\privkey.pem" -out "%CERT_DIR%\fullchain.pem"
if %errorlevel% neq 0 (
    echo [错误] 证书生成失败！
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 证书生成成功！
echo ==========================================
echo.
echo 证书文件位置:
echo   - 私钥: %CERT_DIR%\privkey.pem
echo   - 证书: %CERT_DIR%\fullchain.pem
echo.
echo 注意事项:
echo 1. 自签名证书仅用于开发测试
echo 2. 生产环境请使用Let's Encrypt证书
echo 3. 浏览器会显示警告，需要手动信任
echo.
pause
