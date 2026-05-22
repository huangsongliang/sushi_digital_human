# 监控服务说明

## 📊 系统监控

### 方式1：直接查看指标（无需Docker）
直接访问后端暴露的Prometheus指标：
- **地址**：http://localhost:8000/metrics
- **说明**：无需启动Docker即可查看所有系统指标

### 方式2：Docker监控服务（可选）

#### 🐳 启动监控服务
```bash
# 使用Docker Compose启动Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d
```

#### 🔗 访问地址
| 服务 | 地址 | 默认账号密码 |
|------|------|-------------|
| Prometheus | http://localhost:9090 | 无 |
| Grafana | http://localhost:3001 | admin/admin |

#### 🛑 Docker镜像下载失败？
如果遇到镜像下载403错误，可能是镜像源限制，可以：
1. 暂时跳过监控，直接访问 http://localhost:8000/metrics
2. 配置Docker使用其他镜像源
3. 使用Docker Hub官方源

## 📈 Prometheus指标说明

### 关键指标
| 指标名称 | 说明 |
|----------|------|
| `sushi_requests_total` | API总请求数 |
| `sushi_request_duration_seconds` | 请求耗时分布 |
| `sushi_llm_calls_total` | LLM调用次数 |
| `sushi_llm_token_usage` | LLM token使用量 |
| `sushi_retrieval_duration_seconds` | 检索耗时 |
| `sushi_retrieval_documents_found` | 检索到的文档数量 |
| `sushi_memory_operations_total` | 内存操作次数 |
| `sushi_errors_total` | 错误计数 |
| `sushi_uptime_seconds` | 系统运行时间 |
| `sushi_active_sessions` | 活跃会话数 |

## 🎯 健康检查端点

| 端点 | 说明 |
|------|------|
| `/health` | 完整健康检查 |
| `/health/liveness` | 存活检查 |
| `/health/readiness` | 就绪检查 |
