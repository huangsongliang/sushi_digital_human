#!/usr/bin/env python3
"""
GitHub CI/CD 状态检查工具 - 自动版本
无需交互，直接获取最新状态
"""

import subprocess
import sys
import os
import json
from pathlib import Path


def get_gh_path():
    """获取 GitHub CLI 的路径"""
    # 先尝试直接运行
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True)
        if result.returncode == 0:
            return ["gh"]
    except:
        pass

    # 尝试常见安装路径
    possible_paths = [
        r"D:\github cli\gh.exe",
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ 找到 GitHub CLI: {path}")
            return [path]

    return None


def run_gh_command(args, capture_output=True):
    """运行 GitHub CLI 命令"""
    try:
        gh_path = get_gh_path()
        if gh_path is None:
            return False, "", "GitHub CLI 未找到"

        command = gh_path + args
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=Path(__file__).parent.parent,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_ci_status():
    """获取最新的 CI 状态"""
    print("=" * 70)
    print("📊 GitHub CI/CD 最新运行状态")
    print("=" * 70)

    success, stdout, stderr = run_gh_command(["run", "list", "-L", "3"])
    if not success:
        print(f"❌ 获取失败: {stderr}")
        return

    lines = stdout.strip().split("\n")
    if len(lines) >= 2:
        print("最近的 CI 运行:")
        print("-" * 70)

        for i, line in enumerate(lines[:3], 1):
            parts = line.split()
            if len(parts) >= 4:
                workflow_name = " ".join(parts[1:-4])
                status = parts[-4]
                branch = parts[-3]
                time = parts[-2]
                print(f"\n{i}. Workflow: {workflow_name}")
                print(f"   状态: {status}")
                print(f"   分支: {branch}")
                print(f"   时间: {time}")

                if status == "success":
                    print("   ✅ 通过")
                elif status == "failure":
                    print("   ❌ 失败")

    print("\n" + "=" * 70)


def get_latest_logs():
    """获取最新的 CI 日志并保存"""
    print("\n" + "=" * 70)
    print("📝 获取最新 CI 日志")
    print("=" * 70)

    success, stdout, stderr = run_gh_command(
        ["run", "list", "-L", "1", "--json", "databaseId"]
    )
    if not success or not stdout.strip():
        print(f"❌ 无法获取 Run ID: {stderr}")
        return

    try:
        data = json.loads(stdout)
        if data and len(data) > 0:
            run_id = str(data[0]["databaseId"])
            print(f"最新 Run ID: {run_id}")
        else:
            print("❌ 无法解析 Run ID")
            return
    except json.JSONDecodeError as e:
        print(f"❌ 解析 JSON 失败: {e}")
        return

    success, stdout, stderr = run_gh_command(["run", "view", run_id, "--log"])
    if success:
        log_file = Path(__file__).parent.parent / f"ci_logs_{run_id}.txt"
        log_file.write_text(stdout, encoding="utf-8")
        print(f"✅ 日志已保存到: {log_file}")

        print("\n📋 日志最后部分（错误信息）:")
        print("-" * 70)
        lines = stdout.strip().split("\n")
        last_lines = lines[-50:] if len(lines) > 50 else lines
        print("\n".join(last_lines))

        return log_file
    else:
        print(f"❌ 获取日志失败: {stderr}")
        return None


def main():
    print("🍣 苏轼数字人 - GitHub CI/CD 状态检查")
    print("-" * 70)

    if get_gh_path() is None:
        print("\n❌ GitHub CLI 未安装!")
        print("请先安装: https://cli.github.com/")
        print("安装后运行: gh auth login")
        return 1

    get_ci_status()
    log_file = get_latest_logs()

    if log_file:
        print(f"\n💡 如果 CI 失败，请查看日志文件: {log_file}")
        print("您可以将日志内容发给 AI 助手进行分析")

    return 0


if __name__ == "__main__":
    sys.exit(main())
