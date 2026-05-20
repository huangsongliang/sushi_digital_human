@echo off
REM ==========================================
REM [弃用] Let's Encrypt 证书更新脚本 (Windows)
REM ==========================================

echo ==========================================
echo ⚠️  警告: 此脚本已弃用
echo ==========================================
echo.
echo Certbot 官方从 2024 年 2 月起停止了对 Windows 平台的支持。
echo 不再有官方维护、更新和安全修复。
echo.
echo 替代方案:
echo 1. scripts\get_ssl_cert.bat - 使用 acme.sh (推荐)
echo 2. scripts\docker_certbot.bat - 使用 Docker 运行 Certbot
echo.
set /p CHOICE="是否继续使用此脚本? (y/n): "

if /i not "%CHOICE%"=="y" exit /b 0

echo.
echo 如果你坚持使用，请参考以下步骤:
echo.
echo 1. 使用 Certbot Docker 镜像代替
echo    docker run -it --rm -p 80:80 -p 443:443 ^
echo        -v "C:\Certbot:/etc/letsencrypt" ^
echo        -v "C:\Certbot:/var/www/certbot" ^
echo        certbot/certbot certonly --standalone ^
echo        -d your-domain.com -d www.your-domain.com ^
echo        --email your@email.com --agree-tos --non-interactive
echo.
echo 2. 或使用 acme.sh
echo    bash -c "curl https://get.acme.sh ^| sh -s email=your@email.com"
echo    ~/.acme.sh/acme.sh --issue -d your-domain.com --standalone
echo.
echo 建议使用 scripts\get_ssl_cert.bat 获取更好的跨平台支持
echo.
pause
