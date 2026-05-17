# Docker Compose 负载均衡 + 水平扩展

## 架构概述

```
                    ┌─────────────┐
                    │   用户请求   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │  ← 负载均衡器
                    │  (端口 8000)│
                    └──────┬──────┘
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
     │  API 实例 1 │ │API 实例 2│ │  API 实例 3 │
     └──────┬──────┘ └────┬─────┘ └──────┬──────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │  ← 共享存储
                    └─────────────┘
```

## 文件结构

```
sushi_digital_human/
├── docker-compose.simple.yml  # 简化版 Docker Compose
├── Dockerfile                  # API 镜像构建
├── start-docker.bat           # Windows 快速启动脚本
├── requirements.txt           # Python 依赖
├── config/
│   └── nginx/
│       └── nginx.conf         # Nginx 负载均衡配置
└── backend/
    └── utils/
        └── task_manager.py    # 任务管理器（支持 Redis 存储）
```

## 快速开始

### 前置条件

1. 安装 Docker Desktop（Windows）
2. 确保 Docker 正在运行

### 方式一：自动启动（推荐）

双击运行：

```bash
start-docker.bat
```

这个脚本会自动：
1. 检查 Docker 状态
2. 清理旧容器
3. 构建镜像
4. 启动服务（3 个 API 实例）
5. 等待服务就绪

### 方式二：手动启动

```bash
# 1. 构建镜像
docker-compose -f docker-compose.simple.yml build

# 2. 启动服务（3 个 API 实例）
docker-compose -f docker-compose.simple.yml up -d --scale api=3

# 3. 查看日志
docker-compose -f docker-compose.simple.yml logs -f
```

## 访问服务

服务启动后，访问：

- **主 API（负载均衡）**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 常用命令

### 查看服务状态

```bash
docker-compose -f docker-compose.simple.yml ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.simple.yml logs -f

# 只看 API 日志
docker-compose -f docker-compose.simple.yml logs -f api
```

### 水平扩展（增加 API 实例）

```bash
# 扩展到 5 个 API 实例
docker-compose -f docker-compose.simple.yml up -d --scale api=5

# 扩展到 10 个 API 实例
docker-compose -f docker-compose.simple.yml up -d --scale api=10
```

### 减少实例

```bash
# 缩容到 2 个 API 实例
docker-compose -f docker-compose.simple.yml up -d --scale api=2
```

### 停止服务

```bash
# 停止服务但保留数据
docker-compose -f docker-compose.simple.yml down

# 停止并删除所有数据（谨慎）
docker-compose -f docker-compose.simple.yml down -v
```

### 重启服务

```bash
docker-compose -f docker-compose.simple.yml restart
```

## 配置说明

### 修改 API 实例数量

编辑 `docker-compose.simple.yml`：

```yaml
services:
  api:
    deploy:
      replicas: 3  # 修改这个数字
```

或直接用命令扩展。

### 修改资源限制

编辑 `docker-compose.simple.yml`：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 启用/禁用 Redis 任务存储

通过环境变量控制：

```yaml
services:
  api:
    environment:
      - USE_REDIS_STORAGE=true  # 使用 Redis 共享任务
      # 或
      - USE_REDIS_STORAGE=false  # 使用内存存储（单实例）
```

## 性能测试

在本地测试负载均衡效果：

```bash
# 使用测试脚本
python tests/test_async_api.py
```

## 故障排查

### 服务启动失败

1. 检查端口占用：
   ```bash
   netstat -ano | findstr :6379
   netstat -ano | findstr :8000
   ```

2. 查看详细日志：
   ```bash
   docker-compose -f docker-compose.simple.yml logs
   ```

3. 确保 Docker Desktop 有足够资源（建议 4G+ 内存）

### Redis 连接失败

确保 Redis 容器先启动：

```bash
docker-compose -f docker-compose.simple.yml up -d redis
# 等待 10 秒
docker-compose -f docker-compose.simple.yml up -d api
```

### API 健康检查失败

检查：
1. API 容器日志：`docker-compose -f docker-compose.simple.yml logs api`
2. 依赖是否安装成功
3. 环境变量是否正确

## 下一步

要真正实现生产级万人并发：

1. **增加服务器资源**（更多 CPU/内存）
2. **使用 Redis 集群**（而不是单实例）
3. **添加监控**（Prometheus + Grafana）
4. **配置 HTTPS**（证书）
5. **使用 Kubernetes**（大规模部署）

## 总结

当前架构已实现：
- ✅ Nginx 负载均衡
- ✅ API 水平扩展（3 实例）
- ✅ Redis 共享任务存储
- ✅ 自动健康检查
- ✅ 一键启停

适用于：
- 本地开发和测试
- 小规模生产
- 演示和学习
