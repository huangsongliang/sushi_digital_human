# HTTPS 配置指南

本文档详细说明如何为 Sushi Digital Human 项目配置 HTTPS 安全连接。

## 目录

1. [概述](#概述)
2. [证书方案对比](#证书方案对比)
3. [开发环境：自签名证书](#开发环境自签名证书)
4. [生产环境：acme.sh 方案（推荐）](#生产环境acme-sh-方案推荐)
5. [生产环境：Docker Certbot 方案](#生产环境docker-certbot-方案)
6. [云服务商 SSL 证书](#云服务商-ssl-证书)
7. [Nginx 配置](#nginx-配置)
8. [Docker Compose 配置](#docker-compose-配置)
9. [验证 HTTPS 配置](#验证-https-配置)
10. [常见问题](#常见问题)

---

## 概述

HTTPS 配置是生产环境的必要条件，它提供：
- 数据传输加密
- 身份验证
- 防止中间人攻击
- 提升搜索引擎排名

---

## 证书方案对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **自签名证书** | 开发测试 | 快速、无需配置 | 浏览器警告、仅限 localhost |
| **acme.sh** | 生产环境（推荐） | 跨平台、自动续期、轻量 | 需要 Git Bash 或 WSL |
| **Docker Certbot** | 生产环境 | 无需安装额外软件 | 需要 Docker 基础 |
| **云服务商证书** | 企业用户 | 一键部署、自动续期 | 绑定特定云平台 |

### ⚠️ 重要提示

> **Certbot Windows 版本已弃用**
>
> Certbot 官方从 2024 年 2 月起停止了对 Windows 平台的 Beta 支持，不再有官方维护、更新和安全修复。
>
> **推荐使用：**
> 1. **acme.sh** - 跨平台兼容，Git Bash/WLinux/WSL 均可运行
> 2. **Docker Certbot** - 无需安装，使用容器运行

---

## 开发环境：自签名证书

### 前置要求

1. 安装 OpenSSL：
   - 下载：https://slproweb.com/products/Win32OpenSSL.html
   - 或使用 Git Bash 自带的 OpenSSL
   - 确保 OpenSSL 已添加到系统 PATH

### 生成自签名证书

```cmd
scripts\generate_self_signed_cert.bat
```

生成的证书文件位于：
- `ssl/privkey.pem` - 私钥
- `ssl/fullchain.pem` - 证书链

### 使用自签名证书

编辑 `config/nginx/conf.d/https.conf`，将域名改为 `localhost`：

```nginx
server_name localhost;
```

浏览器访问时会显示安全警告，需要手动点击"继续访问"。

---

## 生产环境：acme.sh 方案（推荐）

acme.sh 是一个纯 Shell 脚本实现的 ACME 客户端，跨平台兼容，支持 Git Bash、WSL、Linux 等。

### 前置要求

1. **安装 Git for Windows**：https://git-scm.com/download/win
2. **拥有域名**且 DNS 已解析到服务器 IP

### 方式 1：使用脚本（推荐）

运行交互式脚本：

```cmd
scripts\get_ssl_cert.bat
```

按照提示选择运行环境（Git Bash / WSL）并输入域名和邮箱。

### 方式 2：手动执行

#### 步骤 1：安装 acme.sh

```bash
# 在 Git Bash 或 WSL 中运行
curl https://get.acme.sh | sh -s email=your@email.com
```

#### 步骤 2：申请证书

**HTTP 方式（需要 80 端口可用）：**
```bash
~/.acme.sh/acme.sh --issue -d your-domain.com -d www.your-domain.com --webroot /var/www/html
```

**DNS 方式（不需要开放端口）：**
```bash
~/.acme.sh/acme.sh --issue --dns -d your-domain.com -d www.your-domain.com
# 按提示添加 DNS TXT 记录
```

#### 步骤 3：安装证书到项目

```bash
~/.acme.sh/acme.sh --install-cert -d your-domain.com \
    --key-file "/mnt/d/code/sushi_digital_human/ssl/privkey.pem" \
    --fullchain-file "/mnt/d/code/sushi_digital_human/ssl/fullchain.pem" \
    --reloadcmd "docker exec sushi-nginx nginx -s reload"
```

### 自动续期

acme.sh 会自动添加 cron 任务，通常每 60 天自动续期。

检查续期任务：
```bash
crontab -l | grep acme.sh
```

手动续期：
```bash
~/.acme.sh/acme.sh --renew -d your-domain.com
```

---

## 生产环境：Docker Certbot 方案

使用 Docker 容器运行 Certbot，无需在主机安装 Certbot。

### 前置要求

安装 Docker Desktop：https://docs.docker.com/desktop/install/windows-install/

### 使用脚本

```cmd
scripts\docker_certbot.bat
```

### 手动执行

#### 步骤 1：创建目录

```cmd
mkdir ssl
mkdir acme
```

#### 步骤 2：获取证书

```cmd
docker run --rm -it ^
    -v "%cd%\acme:/acme.sh" ^
    -v "%cd%\ssl:/output" ^
    -p 80:80 ^
    neilpang/acme.sh ^
    --issue -d your-domain.com -d www.your-domain.com ^
    --httpport 80 ^
    --keylength 2048 ^
    --email your@email.com ^
    --standalone
```

#### 步骤 3：复制证书

证书会自动安装到 `ssl/` 目录：
- `ssl/fullchain.pem`
- `ssl/privkey.pem`

#### 步骤 4：自动续期

创建续期脚本 `auto_renew_cert.bat`：

```batch
@echo off
docker run --rm ^
    -v "%cd%\acme:/acme.sh" ^
    -p 80:80 ^
    neilpang/acme.sh ^
    --renew -d your-domain.com -d www.your-domain.com ^
    --httpport 80

if %errorlevel% equ 0 (
    docker exec sushi-nginx nginx -s reload
)
```

设置 Windows 任务计划程序每月运行此脚本。

---

## 云服务商 SSL 证书

如果你的服务器在云平台，可以使用其提供的免费 SSL 证书。

### 阿里云

1. 登录阿里云控制台 → SSL 证书
2. 选择"免费证书" → 立即购买
3. 创建证书 → 填写域名信息
4. DNS 验证（自动添加 TXT 记录）
5. 下载证书（选择 Nginx 类型）

### 腾讯云

1. 登录腾讯云控制台 → SSL 证书
2. 申请免费证书
3. DNS 验证
4. 下载证书（Nginx）

### 使用云服务商证书

1. 下载证书文件：
   - `fullchain.pem` - 证书链
   - `privkey.pem` - 私钥

2. 复制到项目：
   ```cmd
   copy downloaded\fullchain.pem ssl\fullchain.pem
   copy downloaded\privkey.pem ssl\privkey.pem
   ```

3. 大多数云平台支持自动续期，无需手动操作。

---

## Nginx 配置

### 配置文件说明

项目提供了两套 Nginx 配置：

1. **`config/nginx/nginx.conf`** - HTTP 版本（开发用）
2. **`config/nginx/nginx.https.conf`** - HTTPS 版本（生产用）
3. **`config/nginx/conf.d/https.conf`** - HTTPS 站点详细配置

### 启用 HTTPS 配置

#### 步骤 1：修改域名

编辑 `config/nginx/conf.d/https.conf`，替换为你的域名：

```nginx
server_name your-domain.com www.your-domain.com;
```

#### 步骤 2：更新 Nginx 主配置

在 `docker-compose.prod.yml` 中，将 nginx 配置卷挂载改为：

```yaml
volumes:
  - ./config/nginx/nginx.https.conf:/etc/nginx/nginx.conf:ro
  - ./config/nginx/conf.d/:/etc/nginx/conf.d/:ro
```

#### 步骤 3：配置安全头

HTTPS 配置已包含以下安全头：

- **HSTS**：强制浏览器使用 HTTPS
- **X-Frame-Options**：防止点击劫持
- **X-Content-Type-Options**：防止 MIME 类型嗅探
- **X-XSS-Protection**：XSS 防护
- **CSP**：内容安全策略

---

## Docker Compose 配置

### 完整的 HTTPS docker-compose 配置

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: sushi-redis
    ports:
      - "6379:6379"
    command: >
      redis-server
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - sushi-network
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      - ENV=production
      - REDIS_URL=redis://redis:6379/0
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    deploy:
      replicas: 3
    networks:
      - sushi-network
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: sushi-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.https.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/conf.d/:/etc/nginx/conf.d/:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      - api
    networks:
      - sushi-network
    restart: unless-stopped

volumes:
  redis-data:
  nginx-logs:

networks:
  sushi-network:
    driver: bridge
```

### 启动服务

```cmd
# 启动所有服务
docker-compose -f docker-compose.https.yml up -d

# 查看日志
docker-compose -f docker-compose.https.yml logs -f nginx
```

---

## 验证 HTTPS 配置

### 1. 检查 Nginx 配置

```cmd
docker exec sushi-nginx nginx -t
```

应该看到：
```
syntax is ok
test is successful
```

### 2. 测试 SSL 证书

使用在线工具：
- SSL Labs Server Test: https://www.ssllabs.com/ssltest/

或使用命令行：

```cmd
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### 3. 浏览器测试

1. 访问 `http://your-domain.com` - 应该自动重定向到 HTTPS
2. 访问 `https://your-domain.com` - 应该显示安全锁图标

### 4. 检查安全头

使用浏览器开发者工具（F12）→ Network 标签，查看响应头应该包含：
- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`

---

## 常见问题

### Q1: 浏览器显示 "不安全"

**A**: 可能原因：
1. 使用的是自签名证书 - 开发环境正常，生产环境应使用 Let's Encrypt 或云证书
2. 证书域名不匹配 - 检查 `server_name` 配置
3. 证书已过期 - 续期证书

### Q2: acme.sh 安装失败

**A**: 确保在 Git Bash 或 WSL 中运行：
```bash
# Git Bash
bash -c "curl https://get.acme.sh | sh"

# 或使用国内镜像
bash -c "curl https://get.acme.sh | sh -s -- --use-wget"
```

### Q3: 证书获取失败，提示端口占用

**A**: 确保 80 端口未被占用：
```cmd
netstat -ano | findstr :80
```
停止占用 80 端口的服务。

### Q4: DNS 验证失败

**A**: 检查：
1. DNS 记录是否已传播（可能需要等待几分钟）
2. 记录类型是否为 TXT
3. 记录值是否完全匹配

### Q5: 证书续期后需要重启 Nginx 吗？

**A**: 是的，需要重新加载配置：
```cmd
docker exec sushi-nginx nginx -s reload
```

### Q6: 可以使用付费证书吗？

**A**: 可以！付费证书（如 DigiCert、GlobalSign）提供更高级别的信任担保和更长的有效期。
只需将证书文件复制到 `ssl/` 目录即可。

---

## 安全最佳实践

1. ✅ **使用 TLS 1.2+** - 已在配置中启用
2. ✅ **启用 HSTS** - 已配置
3. ✅ **定期更新证书** - 设置自动续期
4. ✅ **使用强密码套件** - 已配置现代套件
5. ✅ **禁用不安全的协议** - 已禁用 SSLv3、TLS 1.0、TLS 1.1
6. ✅ **保护私钥** - 私钥文件权限设为只读，不要提交到 Git
7. ✅ **监控证书有效期** - 设置过期告警

---

## 获取帮助

如遇问题：
1. acme.sh 文档：https://github.com/acmesh-official/acme.sh/wiki
2. Let's Encrypt 文档：https://letsencrypt.org/docs/
3. Docker Certbot：https://certbot.eff.org/instructions

---

## 下一步

配置完 HTTPS 后，建议继续配置：
- [监控告警](./MONITORING_SETUP.md)
- [数据备份](./BACKUP_GUIDE.md)
- [性能优化](./PERFORMANCE_TUNING.md)
