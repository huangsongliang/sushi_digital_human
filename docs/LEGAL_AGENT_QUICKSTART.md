# 法律诉讼智能体 - 新项目快速启动指南

> 从 sushi_digital_human fork 出新项目的最快路径。

---

## 第一步：创建新项目

```bash
# 选项 A：全新项目
mkdir legal_agent && cd legal_agent
git init

# 选项 B：从 sushi 克隆并去历史化
git clone https://github.com/huangsongliang/sushi_digital_human.git legal_agent
cd legal_agent
rm -rf .git && git init   # 干净历史（推荐，已清理敏感信息）
```

---

## 第二步：必须复制的文件

### 从 sushi_digital_human 复制到新项目根目录

```bash
# 在 legal_agent 项目根目录执行

# 1. 方案文档
cp ../sushi_digital_human/docs/LEGAL_AGENT_PLAN.md ./README.md

# 2. 代码约定（复制到 .codebuddy 规则目录）
mkdir -p .codebuddy/rules/project/
cp ../sushi_digital_human/.codebuddy/rules/legal-agent-conventions.md .codebuddy/rules/project/

# 3. 复用基础架构（挑选需要的模块）
# - backend/core/          # 配置、安全、鉴权
# - backend/database/       # 数据库模型
# - backend/retrieval/      # 检索引擎（裁掉非法律部分）
# - backend/chain/          # LangChain 链（保留 prompt 模板架构）
# - backend/generator/      # LLM 生成器
# - backend/utils/          # 日志、性能、限流
# - frontend/src/stores/    # Pinia（鉴权 store 可复用）
# - frontend/src/utils/     # request.ts（HTTP 客户端）
```

### 不需要复制的（裁掉）

```
backend/api/chat.py        → 替换为 legal agent 专用 API
backend/api/documents.py   → 替换为卷宗上传 API
frontend/views/Home.vue    → 替换为法律专用首页
docker-compose.prod.yml    → 简化，去掉非法律相关服务
tests/                     → 全新编写
docs/*.md                  → 保留 LEGAL_AGENT_PLAN.md，删除 sushi 相关文档
```

---

## 第三步：搭建 MVP 骨架（Day 1 可以完成的）

### 3.1 后端基础

```bash
# 创建法律专用目录
mkdir -p backend/agent/legal
mkdir -p backend/kg/legal
mkdir -p backend/retrieval/legal
mkdir -p backend/api/legal
```

```python
# backend/agent/legal/__init__.py
"""法律诉讼 Agent 核心模块

MVP 阶段：单 Agent 处理分析、检索、报告生成
"""
```

```python
# backend/kg/legal/models.py
"""法律领域知识图谱实体模型"""
from enum import Enum

class LegalEntityType(str, Enum):
    PLAINTIFF = "PLAINTIFF"
    DEFENDANT = "DEFENDANT"
    THIRD_PARTY = "THIRD_PARTY"
    WITNESS = "WITNESS"
    AGENT = "AGENT"
    LAW_FIRM = "LAW_FIRM"
    JUDGE = "JUDGE"
    COURT = "COURT"
    EVIDENCE = "EVIDENCE"
    LEGAL_ARTICLE = "LEGAL_ARTICLE"
    PRECEDENT = "PRECEDENT"
    LITIGATION_REQUEST = "LITIGATION_REQUEST"
    DEFENSE = "DEFENSE"
    COUNTERCLAIM = "COUNTERCLAIM"
    LEGAL_RELATION = "LEGAL_RELATION"
    CAUSE_OF_ACTION = "CAUSE_OF_ACTION"
```

```python
# backend/api/legal/router.py
"""法律 Agent API 路由 - MVP 阶段"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/legal", tags=["legal"])

@router.post("/analyze")
async def analyze_case():
    """诉状分析 - MVP 核心入口"""
    pass

@router.post("/report")
async def generate_report():
    """生成法律报告"""
    pass
```

### 3.2 前端基础

```bash
mkdir -p frontend/src/views/legal
mkdir -p frontend/src/components/legal
```

```vue
<!-- frontend/src/views/legal/CaseAnalyzer.vue -->
<template>
  <div class="case-analyzer">
    <el-upload drag :on-success="handleUpload">
      <el-icon><UploadFilled /></el-icon>
      <div>拖拽或点击上传卷宗 PDF</div>
    </el-upload>

    <el-card v-if="analysisResult" class="result-card">
      <template #header>分析结果</template>
      <!-- 案件摘要、事实梳理、法律分析 -->
    </el-card>
  </div>
</template>
```

---

## 第四步：MVP 开发优先级

按时间顺序排列的开发 checklist：

- [ ] **Day 1-2**：项目骨架 + PDF 上传 + OCR 文字提取
- [ ] **Day 3-5**：法律 NER 抽取（通用 NER + LLM few-shot）
- [ ] **Day 6-8**：简单知识图谱构建（人物-证据关系）
- [ ] **Day 9-11**：向量检索问答（复用 RAG 链）
- [ ] **Day 12-14**：固定模板报告生成（LLM 填槽）
- [ ] **Day 15-18**：前端页面开发（上传 + 分析 + 报告展示）
- [ ] **Day 19-21**：联调测试 + Bug 修复

---

## 第五步：`.gitignore` 最小配置

```gitignore
# 环境
.env
venv/
.venv/

# 构建
dist/
build/
*.egg-info/

# Python
__pycache__/
*.pyc

# 编辑器
.idea/
.vscode/

# 数据
data/
chroma_db/

# 日志
logs/
*.log

# IDE 本地配置
.trae/
.playwright-cli/
.codebuddy/memory/
.codebuddy/rules/tcb/
.codebuddy/plans/
```

---

## 关键提醒

1. **先跑通再优化**：MVP 阶段不要追求完美架构
2. **裁掉非法律代码**：sushi 的文档管理、聊天系统、监控等模块全部移除
3. **单 Agent 起步**：一个 Agent 完成分析+检索+报告，第二阶段再拆分
4. **OCR 先用 EasyOCR**：中文法律文档对 PaddleOCR 更友好，但 EasyOCR 集成更快
5. **判例库延后**：MVP 用网络搜索代替，第二阶段再建库
