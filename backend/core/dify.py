"""
Dify 平台集成模块
支持将 RAG 能力作为 Dify 工具供工作流调用
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

import requests

from backend.core.config import settings
from backend.retrieval import get_hybrid_retriever
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DifyTool:
    """Dify 工具定义"""

    name: str
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    tool_type: str = "function"


@dataclass
class DifyMessage:
    """Dify 消息格式"""

    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_result: Optional[Dict[str, Any]] = None


@dataclass
class DifyToolCall:
    """Dify 工具调用"""

    tool_name: str
    arguments: Dict[str, Any]
    task_id: str


class DifyIntegration:
    """Dify 集成管理器"""

    def __init__(self):
        self._api_key = None
        self._base_url = "https://api.dify.ai/v1"

    def configure(self, api_key: str, base_url: str = "https://api.dify.ai/v1"):
        """配置 Dify API"""
        self._api_key = api_key
        self._base_url = base_url
        logger.info("Dify 集成已配置")

    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def get_rag_search_tool(self) -> DifyTool:
        """获取 RAG 检索工具定义（符合 Dify 工具规范）"""
        return DifyTool(
            name="search_documents",
            description="搜索企业文档知识库，获取相关文档内容。用于回答关于企业文档的问题。",
            parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "required": True,
                    "description": "用户的查询问题",
                },
                {
                    "name": "top_k",
                    "type": "integer",
                    "required": False,
                    "description": "返回文档数量，默认 3",
                    "default": 3,
                },
                {
                    "name": "use_rag",
                    "type": "boolean",
                    "required": False,
                    "description": "是否使用 RAG 检索，默认 True",
                    "default": True,
                },
            ],
        )

    def search_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索文档（核心 RAG 能力）

        Args:
            query: 用户查询
            top_k: 返回数量

        Returns:
            文档列表
        """
        retriever = get_hybrid_retriever()
        results = retriever.search(query, top_k=top_k, use_bm25=True, use_vector=True, use_rerank=True)

        # 转换为 Dify 工具返回格式
        formatted_results = []
        for i, doc in enumerate(results):
            formatted_results.append(
                {
                    "id": str(i),
                    "content": doc.get("content", ""),
                    "score": doc.get("score", 0),
                    "metadata": doc.get("metadata", {}),
                }
            )

        return formatted_results

    def execute_tool(self, tool_call: DifyToolCall) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            工具执行结果
        """
        tool_name = tool_call.tool_name

        if tool_name == "search_sushi_documents":
            query = tool_call.arguments.get("query", "")
            top_k = tool_call.arguments.get("top_k", 3)

            if not query:
                return {"success": False, "error": "query 参数不能为空"}

            try:
                results = self.search_documents(query, top_k)
                return {
                    "success": True,
                    "data": {
                        "documents": results,
                        "query": query,
                        "count": len(results),
                    },
                    "message": f"成功检索到 {len(results)} 条相关文档",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            return {"success": False, "error": f"未知工具: {tool_name}"}

    def generate_tool_response(self, task_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成 Dify 工具响应格式

        Args:
            task_id: Dify 任务 ID
            result: 工具执行结果

        Returns:
            Dify 格式的响应
        """
        if result.get("success"):
            documents = result.get("data", {}).get("documents", [])

            # 构建总结内容
            summaries = []
            for doc in documents:
                content = doc.get("content", "")
                if content:
                    summaries.append(content[:200] + "..." if len(content) > 200 else content)

            return {
                "task_id": task_id,
                "status": "success",
                "content": "\n\n".join(summaries),
                "tool_result": {
                    "type": "text",
                    "content": json.dumps(result.get("data", {}), ensure_ascii=False),
                },
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "content": f"工具执行失败: {result.get('error', '未知错误')}",
                "tool_result": {
                    "type": "error",
                    "content": result.get("error", "未知错误"),
                },
            }

    # ==================== Dify API 调用 ====================

    def create_application(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        在 Dify 中创建应用

        Args:
            name: 应用名称
            description: 应用描述

        Returns:
            创建结果
        """
        url = f"{self._base_url}/apps"
        payload = {"name": name, "description": description, "app_type": "chat"}

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"创建 Dify 应用失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_application(self, app_id: str) -> Dict[str, Any]:
        """获取应用信息"""
        url = f"{self._base_url}/apps/{app_id}"

        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取 Dify 应用信息失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def list_applications(self) -> Dict[str, Any]:
        """获取应用列表"""
        url = f"{self._base_url}/apps"

        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取 Dify 应用列表失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def update_application(
        self, app_id: str, name: Optional[str] = None, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新应用信息"""
        url = f"{self._base_url}/apps/{app_id}"
        payload = {}

        if name:
            payload["name"] = name
        if description:
            payload["description"] = description

        try:
            response = requests.put(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"更新 Dify 应用失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def delete_application(self, app_id: str) -> Dict[str, Any]:
        """删除应用"""
        url = f"{self._base_url}/apps/{app_id}"

        try:
            response = requests.delete(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            logger.error(f"删除 Dify 应用失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def chat_completion(self, app_id: str, message: str, user_id: str = "default") -> Dict[str, Any]:
        """
        调用 Dify 聊天接口

        Args:
            app_id: 应用 ID
            message: 用户消息
            user_id: 用户 ID

        Returns:
            聊天响应
        """
        url = f"{self._base_url}/chat-messages"
        payload: Dict[str, Any] = {
            "app_id": app_id,
            "user_id": user_id,
            "inputs": {},
            "query": message,
            "response_mode": "streaming",
            "user": {"id": user_id, "name": "用户"},
        }

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, stream=True, timeout=60)
            response.raise_for_status()

            # 处理流式响应
            results = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[5:])
                            results.append(data)
                        except json.JSONDecodeError:
                            pass

            return {"success": True, "data": results}
        except Exception as e:
            logger.error(f"Dify 聊天调用失败: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局 Dify 集成实例
dify_integration = DifyIntegration()


def get_dify_integration() -> DifyIntegration:
    """获取 Dify 集成实例"""
    return dify_integration


# ==================== Dify Webhook 处理器 ====================


class DifyWebhookHandler:
    """Dify Webhook 处理器"""

    def __init__(self):
        self._handlers = {}

    def register_handler(self, event_type: str, handler):
        """注册事件处理器"""
        self._handlers[event_type] = handler

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 Dify Webhook 事件

        Args:
            event_type: 事件类型
            payload: 事件数据

        Returns:
            处理结果
        """
        handler = self._handlers.get(event_type)

        if handler:
            try:
                result = handler(payload)
                return {"success": True, "data": result}
            except Exception as e:
                logger.error(f"处理 {event_type} 事件失败: {str(e)}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"未注册 {event_type} 事件处理器"}


# 全局 Webhook 处理器
webhook_handler = DifyWebhookHandler()


def get_webhook_handler() -> DifyWebhookHandler:
    """获取 Webhook 处理器"""
    return webhook_handler
