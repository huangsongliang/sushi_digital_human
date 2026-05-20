#!/usr/bin/env python3
"""
本地 CI/CD 检查脚本 - Python 版本
用于在提交代码前运行与 GitHub Actions 相同的检查
跨平台支持：Windows, macOS, Linux
"""

import sys
import subprocess
import os
from pathlib import Path


# 颜色代码
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


# 如果是 Windows 且不支持 ANSI 颜色，禁用颜色
if sys.platform == "win32":
    try:
        import colorama

        colorama.init()
    except ImportError:
        Colors.GREEN = ""
        Colors.RED = ""
        Colors.YELLOW = ""
        Colors.CYAN = ""
        Colors.RESET = ""
        Colors.BOLD = ""


def print_header(text):
    print(f"\n{Colors.CYAN}{'=' * 40}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 40}{Colors.RESET}\n")


def print_step(step_num, total_steps, title):
    print(f"{Colors.YELLOW}📋 步骤 {step_num}/{total_steps}: {title}{Colors.RESET}")
    print(f"{Colors.YELLOW}{'-' * 40}{Colors.RESET}")


def print_check_result(check_name, passed):
    if passed:
        print(f"{Colors.GREEN}✅ {check_name}{Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ {check_name}{Colors.RESET}")
    return passed


def run_command(cmd, description):
    """运行命令并返回是否成功"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=Path(__file__).parent.parent)
        return result.returncode == 0
    except Exception as e:
        print(f"{Colors.RED}错误: {e}{Colors.RESET}")
        return False


def main():
    print_header("🍣 苏轼数字人 - 本地 CI/CD 检查")

    all_passed = True
    steps = [
        (
            "代码风格检查 (Flake8)",
            "uv run flake8 backend/ --max-line-length=120 --ignore=E501,W503,W291,W293,F401,F841,E302,F821",
        ),
        ("类型检查 (Mypy)", "uv run mypy backend/ --ignore-missing-imports"),
        ("单元测试", "uv run pytest tests/unit/ -v --tb=short"),
    ]

    for i, (title, cmd) in enumerate(steps, 1):
        print_step(i, len(steps), title)
        passed = run_command(cmd, title)
        if not print_check_result(title, passed):
            all_passed = False
        print()

    # 总结
    print_header("检查结果总结")
    if all_passed:
        print(
            f"{Colors.GREEN}{Colors.BOLD}🎉 所有检查通过！可以安全提交代码。{Colors.RESET}"
        )
    else:
        print(
            f"{Colors.RED}{Colors.BOLD}⚠️  部分检查失败，请修复问题后再提交。{Colors.RESET}"
        )
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
