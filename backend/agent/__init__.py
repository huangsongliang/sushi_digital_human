"""Agent 核心模块 - 支持多轮对话和工具调用"""

from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from backend.chain.rag_chain import get_rag_chain
from backend.generator import get_async_llm
from backend.memory.conversation import ConversationMemory as RedisConversationMemory
from backend.utils.logger import get_logger
from backend.chain.summary_chain import SummaryType

logger = get_logger(__name__)


class DocumentQATool:
    """RAG知识库问答工具"""

    name = "document_qa"
    description = "用于回答关于文档知识库的问题，包括企业文档、政策文件、产品手册、技术文档等内容。"

    def __init__(self):
        self.rag_chain = get_rag_chain()

    async def run(self, query: str) -> Dict[str, Any]:
        """执行RAG问答"""
        logger.info(f"RAG工具执行查询: {query[:50]}...")
        result = await self.rag_chain.async_run(query=query, use_rag=True)
        return {"answer": result.get("answer", ""), "sources": result.get("references", []), "query": query}


class CalculatorTool:
    """计算器工具 - 用于执行数学计算"""

    name = "calculator"
    description = "用于执行数学计算，包括加减乘除、幂运算、平方根等。"

    def run(self, expression: str) -> str:
        """执行数学计算"""
        logger.info(f"计算器工具执行: {expression}")
        try:
            import ast
            import operator

            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_expr(node):
                if isinstance(node, ast.Constant):
                    return node.value
                if isinstance(node, ast.BinOp):
                    left = eval_expr(node.left)
                    right = eval_expr(node.right)
                    op_type = type(node.op)
                    if op_type in operators:
                        return operators[op_type](left, right)
                if isinstance(node, ast.UnaryOp):
                    if isinstance(node.op, ast.USub):
                        return -eval_expr(node.operand)
                raise ValueError(f"不支持的操作: {ast.dump(node)}")

            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body)
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算失败: {str(e)}"


class SummaryTool:
    """对话总结工具"""

    name = "summarize"
    description = "用于总结对话内容或长文本。"

    def run(self, text: str) -> str:
        """总结文本"""
        logger.info(f"总结工具处理: {text[:30]}...")
        from backend.chain.summary_chain import summary_chain

        result = summary_chain.summarize_text(text, summary_type=SummaryType.CONCISE)
        return result.content


class AgentManager:
    """Agent管理器 - 支持多轮对话和工具调用"""

    def __init__(self):
        self.llm = get_async_llm()
        self.tools = self._initialize_tools()
        logger.info("Agent管理器初始化完成")

    def _initialize_tools(self) -> List[Tool]:
        """初始化工具列表"""
        tools = []

        rag_tool = DocumentQATool()
        tools.append(Tool(name=rag_tool.name, func=lambda q: rag_tool.run(q), description=rag_tool.description))

        calc_tool = CalculatorTool()
        tools.append(Tool(name=calc_tool.name, func=calc_tool.run, description=calc_tool.description))

        summary_tool = SummaryTool()
        tools.append(Tool(name=summary_tool.name, func=summary_tool.run, description=summary_tool.description))

        logger.info(f"已加载 {len(tools)} 个工具")
        return tools

    async def run(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """执行Agent对话（支持多轮对话）"""
        logger.info(f"Agent开始处理查询: {query[:50]}...")

        history_messages: List[BaseMessage] = []
        if session_id:
            redis_memory = RedisConversationMemory(session_id)
            history = await redis_memory.get_full_history()
            for msg in history:
                if msg.role == "user":
                    history_messages.append(HumanMessage(content=msg.content))
                else:
                    history_messages.append(AIMessage(content=msg.content))

        tools_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

        system_prompt = f"""
你是一个智能助手，擅长使用工具解决问题。

可用工具：
{tools_descriptions}

请分析用户问题，决定是否调用工具。
如果需要调用工具，请输出JSON格式：
{{"tool": "工具名", "args": {{"参数名": "参数值"}}}}

如果不需要调用工具，直接回答用户问题即可。
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessage(content="{input}"),
            ]
        )

        prompt_text = prompt.format(input=query, history=history_messages)
        llm_result = await self.llm.invoke(prompt_text)
        response_text = llm_result.output["choices"][0]["message"]["content"]

        try:
            import json

            tool_call = json.loads(response_text)
            tool_name = tool_call.get("tool")
            tool_args = tool_call.get("args", {})

            for tool in self.tools:
                if tool.name == tool_name:
                    logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")
                    tool_result = tool.func(**tool_args)

                    if session_id:
                        await redis_memory.save_message("assistant", f"工具[{tool_name}]: {str(tool_result)}")

                    return {
                        "answer": str(tool_result),
                        "sources": [],
                        "tool_used": tool_name,
                        "thought": f"使用工具 {tool_name} 完成查询",
                    }

            return {"answer": f"未知工具: {tool_name}", "sources": []}

        except (json.JSONDecodeError, ValueError):
            if session_id:
                await redis_memory.save_message("user", query)
                await redis_memory.save_message("assistant", response_text)

            return {"answer": response_text, "sources": [], "tool_used": None, "thought": "直接回答用户问题"}


_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """获取Agent管理器实例"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        logger.info("Agent管理器已初始化")
    return _agent_manager
