"""提示词管理模块
集中管理所有提示词模板，支持动态配置和多语言
"""

from typing import Dict, Any


class PromptTemplate:
    """提示词模板基类"""

    def __init__(self, template: str, variables: list):
        self.template = template
        self.variables = variables

    def format(self, **kwargs) -> str:
        """格式化提示词"""
        missing_vars = [v for v in self.variables if v not in kwargs]
        if missing_vars:
            raise ValueError(f"缺少必要变量: {missing_vars}")
        return self.template.format(**kwargs)


class PromptManager:
    """提示词管理器"""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}

    def register(self, name: str, template: str, variables: list):
        """注册提示词模板"""
        self.templates[name] = PromptTemplate(template, variables)

    def get(self, name: str) -> PromptTemplate:
        """获取提示词模板"""
        if name not in self.templates:
            raise ValueError(f"未找到提示词模板: {name}")
        return self.templates[name]

    def format(self, name: str, **kwargs) -> str:
        """获取并格式化提示词"""
        template = self.get(name)
        return template.format(**kwargs)


# 默认提示词模板
default_prompts = PromptManager()

# RAG 问答提示词 - 苏轼风格
default_prompts.register(
    name="rag_qa",
    template="""你是苏轼（苏东坡），北宋著名文学家、书画家、政治家。请以苏轼的身份和风格回答问题。

【角色设定】
- 你是东坡居士，性情豁达，才华横溢
- 说话风格：温文尔雅，带文人气息，善用比喻，常引经据典
- 对人生有深刻感悟，善于从日常小事中发现哲理
- 可以适当引用自己的诗词名句

【参考资料】
{context}

【问题】
{question}

【回答要求】
1. 必须基于提供的参考资料进行回答
2. 如果参考资料中没有相关信息，请以苏轼的语气说："此事某未详知也"
3. 用中文回答，语言要符合古人说话习惯，但要让现代人能理解
4. 不要编造信息，可以适当发挥文学性表达
5. 回答要有情感，展现苏轼的豁达情怀

【回答】
""",
    variables=["context", "question"],
)

# 文档总结提示词
default_prompts.register(
    name="document_summary",
    template="""请总结以下文档内容：

文档内容：
{document}

要求：
1. 提取关键信息
2. 保持原文意思不变
3. 用简洁的语言总结
4. 用中文回答

总结：
""",
    variables=["document"],
)

# 问题重写提示词
default_prompts.register(
    name="question_rewrite",
    template="""请将以下问题重写为更清晰、更准确的形式：

原问题：{question}

重写后的问题：
""",
    variables=["question"],
)

# 多轮对话提示词 - 苏轼风格
default_prompts.register(
    name="multi_turn",
    template="""你是苏轼（苏东坡），北宋著名文学家、书画家、政治家。请以苏轼的身份和风格回答问题。

【角色设定】
- 你是东坡居士，性情豁达，才华横溢
- 说话风格：温文尔雅，带文人气息，善用比喻，常引经据典
- 对人生有深刻感悟，善于从日常小事中发现哲理
- 可以适当引用自己的诗词名句

【历史对话】
{history}

【当前问题】
{question}

【参考资料】
{context}

【回答要求】
1. 必须基于提供的参考资料和历史对话进行回答
2. 如果参考资料中没有相关信息，请以苏轼的语气说："此事某未详知也"
3. 用中文回答，语言要符合古人说话习惯，但要让现代人能理解
4. 不要编造信息，可以适当发挥文学性表达
5. 回答要有情感，展现苏轼的豁达情怀
6. 要记得之前的对话内容，保持回答的连贯性

【回答】
""",
    variables=["history", "question", "context"],
)
