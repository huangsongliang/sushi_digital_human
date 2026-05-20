# CI/CD 本地检查工具

## 概述

本目录包含用于在本地运行 CI/CD 检查的工具，帮助您在提交代码前发现并修复问题，避免等待 GitHub Actions 运行。

## 工具列表

### 1. local_ci_check.py (推荐)

跨平台的 Python 脚本，运行与 GitHub Actions 相同的检查。

**使用方法：**

```bash
# 在项目根目录运行
uv run python scripts/local_ci_check.py
```

**功能：**
- ✅ Flake8 代码风格检查
- ✅ Mypy 类型检查
- ✅ 单元测试
- 🎨 彩色输出，友好的界面

### 2. local_ci_check.ps1 (Windows PowerShell)

专为 Windows PowerShell 设计的检查脚本。

**使用方法：**

```powershell
.\scripts\local_ci_check.ps1
```

### 3. github_ci_helper.py (GitHub CI 辅助工具)

通过 GitHub CLI 获取和分析 CI/CD 运行状态和日志。

**前置要求：**

1. 安装 GitHub CLI: https://cli.github.com/
2. 运行 `gh auth login` 进行登录

**使用方法：**

```bash
uv run python scripts/github_ci_helper.py
```

**功能：**
- 📊 查看最近的 Workflow 运行状态
- 🔍 查找最近失败的 Workflow
- 📝 获取详细日志并保存到文件
- 💡 一键准备好日志供 AI 助手分析

## 工作流程建议

### 推荐的开发工作流：

1. **编写代码**
2. **在提交前运行本地检查**
   ```bash
   uv run python scripts/local_ci_check.py
   ```
3. **修复发现的问题**
4. **提交代码**
5. **推送到远程仓库**

### 检查内容说明：

| 检查项 | 说明 | 重要性 |
|--------|------|--------|
| Flake8 | 代码风格和语法检查 | 🔴 必须通过 |
| Mypy | 类型检查（可选，用于发现潜在问题） | 🟡 建议修复 |
| 单元测试 | 核心功能测试 | 🔴 必须通过 |

## 🔐 关于 GitHub API 访问权限

### 为什么 AI 助手无法直接访问 GitHub API

出于安全考虑，AI 助手无法直接：
- 直接访问您的 GitHub 账户
- 获取 API 密钥或令牌
- 直接读取仓库的 Actions 日志

### ✅ 替代方案（推荐）

使用 `github_ci_helper.py` 工具，它可以：
1. 在您的本地运行（通过 GitHub CLI）访问 GitHub
2. 获取 CI/CD 日志
3. 将日志保存到文件
4. 您可以将日志文件内容发给我分析

这样既安全又方便！

## CI/CD 错误日志获取

### 方法 1：使用辅助工具（推荐）

```bash
uv run python scripts/github_ci_helper.py
```

选择选项 3 可以自动获取日志并保存到文件。

### 方法 2：手动获取 GitHub Actions 错误日志：

1. 访问您的 GitHub 仓库
2. 点击 **Actions** 标签页
3. 选择失败的 workflow run
4. 点击失败的 job
5. 查看详细的日志输出

### 将错误日志提供给 AI 助手：

当 CI/CD 失败时，您可以：

1. 复制错误日志内容
2. 发送给我进行分析
3. 我会帮您定位问题并提供修复方案

## 常见问题

### Q: 为什么本地检查通过了，但 GitHub Actions 还是失败？

A: 可能的原因：
- 环境差异（操作系统、依赖版本等）
- 集成测试需要外部服务（Redis、数据库等）
- 配置差异

**解决方法：** 先运行本地检查，如通过但 CI 仍失败，请将 CI 错误日志发给我分析。

### Q: Mypy 有很多错误需要全部修复吗？

A: 不一定。当前的 CI/CD 配置中 Mypy 检查是宽松的（`2>/dev/null || true`），主要关注 Flake8 和单元测试。但修复 Mypy 错误可以提高代码质量。

### Q: 如何只运行特定的检查？

A: 可以直接运行对应的命令：

```bash
# 只运行 Flake8
uv run flake8 backend/ --max-line-length=120 --ignore=E501,W503,W291,W293,F401,F841,E302,F821

# 只运行单元测试
uv run pytest tests/unit/ -v
```

## 扩展功能建议

未来可以添加：

- [ ] 预提交钩子 (pre-commit) 自动运行检查
- [ ] 集成测试的本地运行脚本
- [ ] 代码覆盖率报告
- [ ] 自动修复脚本

## 相关文件

- [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) - GitHub Actions 配置
- [`pyproject.toml`](../pyproject.toml) - 项目配置
