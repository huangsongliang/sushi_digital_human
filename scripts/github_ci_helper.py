#!/usr/bin/env python3
"""
GitHub CI/CD 辅助工具
需要先安装 GitHub CLI: https://cli.github.com/
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=True):
    """运行命令并返回结果"""
    try:
        import os

        gh_path = os.environ.get("GH_PATH", "gh")
        # 替换命令中的 gh 为完整路径
        if gh_path != "gh" and cmd.startswith("gh "):
            cmd = gh_path + cmd[2:]

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_gh_cli():
    """检查是否安装了 GitHub CLI"""
    # 先尝试直接运行
    success, _, _ = run_command("gh --version")
    if success:
        return True
    # 尝试常见安装路径
    possible_paths = [
        r"D:\github cli\gh.exe",
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    ]
    for path in possible_paths:
        import os

        if os.path.exists(path):
            # 设置环境变量供后续使用
            import os

            os.environ["GH_PATH"] = path
            print(f"✅ 找到 GitHub CLI: {path}")
            return True
    return False


def get_recent_workflows(limit=5):
    """获取最近的 workflow 运行状态"""
    print("=" * 60)
    print("📊 最近的 CI/CD Workflow 运行状态")
    print("=" * 60)

    success, stdout, stderr = run_command(f"gh run list -L {limit}")
    if not success:
        print(f"❌ 获取失败: {stderr}")
        return False

    print(stdout)
    return True


def get_latest_failed_run():
    """获取最近失败的 workflow run"""
    print("\n" + "=" * 60)
    print("🔍 查找最近失败的 Workflow")
    print("=" * 60)

    success, stdout, stderr = run_command("gh run list --status failure -L 1")
    if not success:
        print(f"❌ 获取失败: {stderr}")
        return None

    if not stdout.strip():
        print("✅ 最近没有失败的 workflow!")
        return None

    print(stdout)
    return stdout


def get_run_logs(run_id=None):
    """获取特定 run 的日志"""
    if not run_id:
        # 获取最新的 run
        success, stdout, _ = run_command(
            "gh run list -L 1 --json databaseId -q '.[0].databaseId'"
        )
        if success and stdout.strip():
            run_id = stdout.strip()

    if not run_id:
        print("❌ 无法找到 run ID")
        return

    print("\n" + "=" * 60)
    print(f"📝 获取 Run {run_id} 的日志")
    print("=" * 60)

    success, stdout, stderr = run_command(f"gh run view {run_id} --log")
    if success:
        print(stdout)
        # 同时保存到文件
        log_file = Path(__file__).parent.parent / f"ci_logs_{run_id}.txt"
        log_file.write_text(stdout, encoding="utf-8")
        print(f"\n✅ 日志已保存到: {log_file}")
        print("💡 您可以将此文件内容发给 AI 助手进行分析")
    else:
        print(f"❌ 获取日志失败: {stderr}")


def main():
    print("🍣 苏轼数字人 - GitHub CI/CD 辅助工具")
    print("-" * 60)

    # 检查 GitHub CLI
    if not check_gh_cli():
        print("\n❌ GitHub CLI (gh) 未安装!")
        print("请先安装: https://cli.github.com/")
        print("\n安装后运行: gh auth login")
        return 1

    print("\n✅ GitHub CLI 已就绪")
    print()

    # 显示菜单
    print("请选择操作:")
    print("1. 查看最近的 Workflow 运行状态")
    print("2. 查看最近失败的 Workflow")
    print("3. 获取最新 Workflow 的详细日志")
    print("4. 退出")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        get_recent_workflows()
    elif choice == "2":
        get_latest_failed_run()
    elif choice == "3":
        get_run_logs()
    elif choice == "4":
        print("再见! 👋")
    else:
        print("❌ 无效的选项")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
