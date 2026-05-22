# 测试命令说明

## 单元测试
```bash
# 运行所有单元测试
uv run pytest tests/unit -v

# 运行特定模块测试
uv run pytest tests/unit/[模块名] -v

# 生成覆盖率报告
uv run pytest tests/unit --cov=backend --cov-report=html --cov-report=term
```

## 集成测试
```bash
# 运行集成测试
uv run pytest tests/integration -v

# 运行系统测试
uv run pytest tests/system -v
```

## UI自动化测试
```bash
# 运行UI测试
uv run pytest tests/ui -v

# 生成Playwright测试报告
uv run pytest tests/ui --headed  # 浏览器可见模式
```

## 性能测试
```bash
# 使用Locust进行性能测试
uv run locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 无头模式运行性能测试
uv run locust -f tests/performance/locustfile.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 1m

# 快速基准测试（无需安装Locust）
uv run python tests/performance/benchmark.py
```

## 安全扫描
```bash
# 使用Bandit进行安全扫描
uv run bandit -c bandit.yaml -r backend/ -f json -o bandit-report.json

# 简单的安全扫描
uv run bandit -r backend/
```

## 快速测试命令
```bash
# 运行所有核心测试
uv run pytest tests/unit tests/integration tests/system -v

# 测试覆盖率要求（80%）
uv run pytest tests/unit tests/integration --cov=backend --cov-report=html --cov-fail-under=80
```

## 代码检查
```bash
# 代码格式化
uv run black backend/ tests/

# 代码风格检查
uv run flake8 backend/ tests/

# 类型检查
uv run mypy backend/
```
