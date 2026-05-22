"""CI 失败自动修复脚本

流程：
1. 从 GitHub API 获取失败 Job 的日志
2. 提取错误信息和相关文件名
3. 用 DashScope LLM 分析错误并生成修复代码
4. DashScope 失败时 fallback 到 GitHub Models
5. 创建新分支、提交修复、开 PR
"""

import json
import os
import re
import sys
import traceback
from pathlib import Path

import requests
from github import Github, GithubException

# ==================== 配置 ====================
GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
DASHSCOPE_API_KEY: str = os.environ["DASHSCOPE_API_KEY"]
WORKFLOW_RUN_ID: str = os.environ["WORKFLOW_RUN_ID"]
WORKFLOW_NAME: str = os.environ.get("WORKFLOW_NAME", "CI/CD Pipeline")
REPO_NAME: str = os.environ["REPO"]
HEAD_BRANCH: str = os.environ["HEAD_BRANCH"]
MAX_RETRIES: int = int(os.environ.get("MAX_RETRIES", "3"))

API_BASE: str = f"https://api.github.com/repos/{REPO_NAME}"
HEADERS: dict[str, str] = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_failed_job_logs() -> tuple[str, list[str]]:
    """获取失败 Job 的日志，返回 (日志文本, 相关文件列表)."""
    resp = requests.get(
        f"{API_BASE}/actions/runs/{WORKFLOW_RUN_ID}/jobs",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    jobs: list[dict] = resp.json()["jobs"]

    failed_jobs = [j for j in jobs if j["conclusion"] == "failure"]

    if not failed_jobs:
        return ("No failed jobs found. This shouldn't happen.", [])

    all_logs: list[str] = []
    all_files: set[str] = set()

    for job in failed_jobs:
        log_resp = requests.get(
            f"{API_BASE}/actions/jobs/{job['id']}/logs",
            headers=HEADERS,
            timeout=60,
        )
        log_text: str = log_resp.text

        # 截取最后 8000 字符（避免 token 超限）
        truncated = log_text[-8000:] if len(log_text) > 8000 else log_text

        all_logs.append(
            f"=== Job: {job['name']} ===\n"
            f"Status: {job['conclusion']}\n"
            f"{truncated}"
        )

        # 从日志中提取文件路径
        file_patterns = [
            r'(backend/[\w/]+\.py)',
            r'(frontend/src/[\w/]+\.(?:vue|ts|js))',
            r'(\.github/[\w/]+\.yml)',
            r'File "([^"]+\.py)"',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, log_text)
            for m in matches:
                all_files.add(m)

    return "\n\n".join(all_logs), list(all_files)


def read_source_files(file_paths: list[str]) -> dict[str, str]:
    """读取相关源文件内容."""
    files_content: dict[str, str] = {}
    for path in file_paths[:5]:
        try:
            content = Path(path).read_text(encoding="utf-8")
            files_content[path] = content
        except Exception:
            pass
    return files_content


def ask_dashscope(logs: str, files: dict[str, str]) -> dict | None:
    """用 DashScope 分析并生成修复."""
    try:
        import dashscope
        from dashscope import Generation

        files_section = "\n".join(
            f"### {p}\n```\n{c[:3000]}\n```" for p, c in files.items()
        )

        prompt = (
            f'你是一个 CI/CD 修复专家。以下 CI Pipeline "{WORKFLOW_NAME}" 运行失败。\n\n'
            f"## 失败日志\n```\n{logs[:5000]}\n```\n\n"
            f"## 相关源文件\n{files_section if files_section else '(无法读取相关源文件)'}\n\n"
            "请输出一个 JSON 对象，格式如下：\n"
            '{\n'
            '    "diagnosis": "错误根因分析（中文）",\n'
            '    "files_to_fix": [\n'
            '        {\n'
            '            "path": "文件路径",\n'
            '            "description": "修改说明",\n'
            '            "new_content": "修改后的完整文件内容"\n'
            "        }\n"
            "    ],\n"
            '    "commit_message": "fix: 自动修复 CI 失败 - 简短描述"\n'
            "}\n\n"
            "只修改确实有错误的代码，不要改动正常运行的部分。"
            "如果无法确定问题，返回空的 files_to_fix。"
        )

        response = Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": prompt}],
            result_format="message",
        )

        if response.status_code == 200:
            content = response.output.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        return None

    except Exception as e:
        print(f"[DashScope] 调用失败: {e}")
        return None


def ask_github_models(logs: str, files: dict[str, str]) -> dict | None:
    """Fallback: 用 GitHub Models（免费 GPT-4o-mini）."""
    try:
        files_str = json.dumps(
            {p: c[:2000] for p, c in files.items()}, ensure_ascii=False
        )

        resp = requests.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是 CI/CD 修复专家。"
                            "请分析失败日志并以 JSON 格式输出修复方案。"
                            "输出必须包含 diagnosis, files_to_fix, commit_message 三个字段。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"失败日志:\n{logs[:5000]}\n\n"
                            f"相关文件:\n{files_str}"
                        ),
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        print(f"[GitHub Models] 调用失败: {e}")
        return None


def apply_fixes(fix_result: dict) -> bool:
    """应用修复：创建分支、提交、开 PR."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    fixes: list[dict] = fix_result.get("files_to_fix", [])
    if not fixes:
        print("AI 未发现需要修复的问题")
        return False

    # 创建修复分支
    fix_branch = f"auto-fix/{HEAD_BRANCH}-{WORKFLOW_RUN_ID}"
    default_branch = repo.get_branch(HEAD_BRANCH)
    repo.create_git_ref(
        f"refs/heads/{fix_branch}",
        default_branch.commit.sha,
    )

    for fix in fixes:
        path: str = fix["path"]
        new_content: str = fix["new_content"]
        try:
            file = repo.get_contents(path, ref=fix_branch)
            repo.update_file(
                path,
                f"auto-fix: {fix['description']}",
                new_content,
                file.sha,
                branch=fix_branch,
            )
            print(f"已更新: {path}")
        except GithubException:
            repo.create_file(
                path,
                f"auto-fix: {fix['description']}",
                new_content,
                branch=fix_branch,
            )
            print(f"已创建: {path}")

    # 开 PR
    repo_url = f"https://github.com/{REPO_NAME}"
    commit_msg = fix_result.get("commit_message", "fix: AI 自动修复 CI 失败")
    fixes_md = "\n".join(
        f'- `{f["path"]}`: {f["description"]}' for f in fixes
    )

    pr = repo.create_pull(
        title=f"Auto-fix: {commit_msg}",
        body=(
            f"## AI 自动修复报告\n\n"
            f"**触发原因**: [{WORKFLOW_NAME} 运行失败]"
            f"({repo_url}/actions/runs/{WORKFLOW_RUN_ID})\n\n"
            f"### 诊断\n"
            f"{fix_result.get('diagnosis', 'N/A')}\n\n"
            f"### 修改文件\n"
            f"{fixes_md}\n\n"
            f"---\n"
            f"> 此 PR 由 AI 自动生成，请仔细审核后合并。\n"
        ),
        head=fix_branch,
        base=HEAD_BRANCH,
    )
    print(f"PR 已创建: {pr.html_url}")
    return True


def main() -> None:
    """主流程."""
    print(f"分析 workflow run #{WORKFLOW_RUN_ID}...")

    # 1. 获取日志
    logs, files = get_failed_job_logs()
    print(f"获取到 {len(files)} 个相关文件")

    # 2. 读取源文件
    files_content = read_source_files(files)
    print(f"读取了 {len(files_content)} 个文件")

    # 3. AI 分析（DashScope 优先）
    print("调用 DashScope 分析...")
    result = ask_dashscope(logs, files_content)

    if not result:
        print("DashScope 失败，尝试 GitHub Models fallback...")
        result = ask_github_models(logs, files_content)

    if not result:
        print("所有 AI 服务均失败，无法自动修复")
        sys.exit(0)

    # 4. 应用修复
    applied = apply_fixes(result)
    if not applied:
        print("未产生任何代码变更")


if __name__ == "__main__":
    main()
