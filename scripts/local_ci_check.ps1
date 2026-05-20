# 本地 CI/CD 检查脚本 - PowerShell 版本
# 用于在提交代码前运行与 GitHub Actions 相同的检查

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🍣 苏轼数字人 - 本地 CI/CD 检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"
$AllPassed = $true

# 函数：打印检查结果
function Write-CheckResult {
    param(
        [string]$CheckName,
        [bool]$Passed
    )

    if ($Passed) {
        Write-Host "✅ $CheckName" -ForegroundColor Green
    } else {
        Write-Host "❌ $CheckName" -ForegroundColor Red
        $script:AllPassed = $false
    }
}

# 1. 运行 Flake8 检查
Write-Host "📋 步骤 1/3: 代码风格检查 (Flake8)" -ForegroundColor Yellow
Write-Host "----------------------------------------"
try {
    uv run flake8 backend/ --max-line-length=120 --ignore=E501,W503,W291,W293,F401,F841,E302,F821
    Write-CheckResult "Flake8 检查" $?
} catch {
    Write-CheckResult "Flake8 检查" $false
}
Write-Host ""

# 2. 运行 Mypy 类型检查
Write-Host "📝 步骤 2/3: 类型检查 (Mypy)" -ForegroundColor Yellow
Write-Host "----------------------------------------"
try {
    uv run mypy backend/ --ignore-missing-imports
    Write-CheckResult "Mypy 检查" $?
} catch {
    Write-CheckResult "Mypy 检查" $false
}
Write-Host ""

# 3. 运行单元测试
Write-Host "🧪 步骤 3/3: 单元测试" -ForegroundColor Yellow
Write-Host "----------------------------------------"
try {
    uv run pytest tests/unit/ -v --tb=short
    Write-CheckResult "单元测试" $?
} catch {
    Write-CheckResult "单元测试" $false
}
Write-Host ""

# 总结
Write-Host "========================================" -ForegroundColor Cyan
if ($AllPassed) {
    Write-Host "🎉 所有检查通过！可以安全提交代码。" -ForegroundColor Green
} else {
    Write-Host "⚠️  部分检查失败，请修复问题后再提交。" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

exit $(if ($AllPassed) { 0 } else { 1 })
