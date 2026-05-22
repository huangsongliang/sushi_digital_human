#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动修复代码规范脚本 - 一键修复所有代码风格问题"""

import subprocess
import sys
import os

# 设置默认编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"


def fix_python_code():
    """修复Python代码风格"""
    print("[INFO] 正在修复Python代码...")
    
    print("  - 运行black格式化...")
    code, stdout, stderr = run_command("uv run black backend/ --line-length=120")
    if code != 0:
        print("  [WARN] black警告:", stderr[:500] if stderr else "")
    
    print("  - 运行isort排序导入...")
    code, stdout, stderr = run_command("uv run isort backend/ --profile=black --line-length=120")
    if code != 0:
        print("  [WARN] isort警告:", stderr[:500] if stderr else "")
    
    print("[OK] Python代码修复完成")


def fix_vue_code():
    """修复Vue代码风格"""
    print("[INFO] 正在修复Vue代码...")
    
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    if not os.path.exists(frontend_path):
        print("  [WARN] 未找到frontend目录")
        return
    
    print("  - 运行ESLint自动修复...")
    code, stdout, stderr = run_command("npm run lint -- --fix", cwd=frontend_path)
    if code != 0:
        print("  [WARN] ESLint警告:", stderr[:500] if stderr else "")
    
    print("[OK] Vue代码修复完成")


def check_after_fix():
    """修复后检查"""
    print("\n[INFO] 修复后检查...")
    
    print("  - 检查flake8...")
    code, stdout, stderr = run_command(
        "uv run flake8 backend/ --max-line-length=120 --ignore=E501,W503,W291,W293,F401,F841,E302,F821"
    )
    
    if code == 0:
        print("  [OK] flake8检查通过")
        return True
    else:
        print("  [ERROR] flake8检查失败:")
        print(stderr[:2000] if len(stderr) > 2000 else stderr)
        return False


def main():
    """主函数"""
    print("[START] 开始自动修复代码规范...")
    print()
    
    fix_python_code()
    fix_vue_code()
    
    print()
    print("="*50)
    if check_after_fix():
        print("[DONE] 所有代码修复完成！")
        return 0
    else:
        print("[WARN] 部分问题需要手动修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())