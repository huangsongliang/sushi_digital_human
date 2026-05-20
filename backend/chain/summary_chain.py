"""
智能总结模块
提供多种总结功能：
- 单文档总结
- 多文档总结
- 对话总结
- 关键信息提取
- 摘要生成
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from backend.generator import get_async_llm
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SummaryType(Enum):
    """总结类型枚举"""
    BRIEF = "brief"           # 简短摘要（3-5句话）
    DETAILED = "detailed"     # 详细摘要（1-2段落）
    KEY_POINTS = "key_points" # 要点列表
    STRUCTURED = "structured" # 结构化摘要
    CONCISE = "concise"       # 极简摘要（1句话）


@dataclass
class SummaryResult:
    """总结结果"""
    content: str
    type: SummaryType
    token_count: Optional[int] = None
    source_count: int = 0
    confidence: float = 0.0
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class SummaryChain:
    """总结链"""

    def __init__(self):
        self._llm = get_async_llm()
        self._prompts = {
            SummaryType.BRIEF: """
请对以下内容进行简短总结（3-5句话）：

{content}

要求：
1. 保留核心信息
2. 语言简洁明了
3. 不要遗漏重要数据
4. 用中文回复
""",
            SummaryType.DETAILED: """
请对以下内容进行详细总结（1-2段落）：

{content}

要求：
1. 涵盖所有主要观点
2. 保持逻辑连贯
3. 包含关键数据和结论
4. 用中文回复
""",
            SummaryType.KEY_POINTS: """
请提取以下内容的关键要点：

{content}

要求：
1. 列出5-10个关键点
2. 每个要点简洁明了
3. 按照重要性排序
4. 用中文回复，格式为：
- 要点1
- 要点2
- ...
""",
            SummaryType.STRUCTURED: """
请对以下内容进行结构化总结：

{content}

要求：
1. 按照逻辑结构组织内容
2. 使用标题和子标题
3. 包含关键数据和分析
4. 用中文回复
""",
            SummaryType.CONCISE: """
请用一句话总结以下内容：

{content}

要求：
1. 极其简洁
2. 包含核心信息
3. 用中文回复
"""
        }

    async def summarize_text(self, content: str, summary_type: SummaryType = SummaryType.BRIEF) -> SummaryResult:
        """总结文本内容"""
        if not content or len(content.strip()) == 0:
            return SummaryResult(
                content="内容为空，无法生成总结",
                type=summary_type,
                source_count=0,
                confidence=0.0
            )

        prompt = self._prompts[summary_type].format(content=content[:8000])
        
        try:
            response = await self._llm.generate([prompt])
            result = response.generations[0][0].text.strip()
            
            return SummaryResult(
                content=result,
                type=summary_type,
                token_count=len(result),
                source_count=1,
                confidence=0.9
            )
        except Exception as e:
            logger.error(f"总结生成失败: {str(e)}")
            return SummaryResult(
                content=f"总结生成失败: {str(e)}",
                type=summary_type,
                source_count=1,
                confidence=0.0
            )

    async def summarize_documents(self, documents: List[Dict[str, Any]], summary_type: SummaryType = SummaryType.DETAILED) -> SummaryResult:
        """总结多个文档"""
        if not documents or len(documents) == 0:
            return SummaryResult(
                content="没有文档可总结",
                type=summary_type,
                source_count=0,
                confidence=0.0
            )

        # 合并文档内容
        content = ""
        for i, doc in enumerate(documents, 1):
            doc_content = doc.get("content", "")
            doc_title = doc.get("title", f"文档{i}")
            content += f"【{doc_title}】\n{doc_content}\n\n"

        return await self.summarize_text(content, summary_type)

    async def summarize_conversation(self, messages: List[Dict[str, Any]], summary_type: SummaryType = SummaryType.BRIEF) -> SummaryResult:
        """总结对话历史"""
        if not messages or len(messages) == 0:
            return SummaryResult(
                content="对话为空，无法生成总结",
                type=summary_type,
                source_count=0,
                confidence=0.0
            )

        # 构建对话文本
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        prompt = f"""
请总结以下对话内容：

{conversation_text}

要求：
1. 概括对话主题
2. 列出主要讨论点
3. 总结最终结论或行动项
4. 用中文回复
"""

        try:
            response = await self._llm.generate([prompt])
            result = response.generations[0][0].text.strip()
            
            return SummaryResult(
                content=result,
                type=summary_type,
                token_count=len(result),
                source_count=len(messages),
                confidence=0.9
            )
        except Exception as e:
            logger.error(f"对话总结失败: {str(e)}")
            return SummaryResult(
                content=f"对话总结失败: {str(e)}",
                type=summary_type,
                source_count=len(messages),
                confidence=0.0
            )

    async def extract_key_points(self, content: str, max_points: int = 10) -> List[str]:
        """提取关键要点"""
        prompt = f"""
请从以下内容中提取最多{max_points}个关键要点：

{content}

要求：
1. 只输出要点列表，每行一个
2. 不要编号
3. 简洁明了
4. 用中文回复
"""

        try:
            response = await self._llm.generate([prompt])
            result = response.generations[0][0].text.strip()
            
            # 解析结果
            points = [p.strip() for p in result.split('\n') if p.strip()]
            return points[:max_points]
        except Exception as e:
            logger.error(f"提取要点失败: {str(e)}")
            return []

    async def generate_title(self, content: str, max_length: int = 50) -> str:
        """为内容生成标题"""
        prompt = f"""
请为以下内容生成一个合适的标题（不超过{max_length}字）：

{content[:2000]}

要求：
1. 简洁明了
2. 概括主要内容
3. 用中文回复
4. 只输出标题，不要其他内容
"""

        try:
            response = await self._llm.generate([prompt])
            title = response.generations[0][0].text.strip()
            
            # 清理标题
            title = title.replace('"', '').replace("'", "").strip()
            if len(title) > max_length:
                title = title[:max_length]
            
            return title
        except Exception as e:
            logger.error(f"生成标题失败: {str(e)}")
            return "未命名"


# 全局总结链实例
summary_chain = SummaryChain()


async def summarize_text(content: str, summary_type: str = "brief") -> Dict[str, Any]:
    """总结文本内容（对外接口）"""
    try:
        summary_type_enum = SummaryType[summary_type.upper()]
    except KeyError:
        summary_type_enum = SummaryType.BRIEF

    result = await summary_chain.summarize_text(content, summary_type_enum)
    
    return {
        "content": result.content,
        "type": result.type.value,
        "token_count": result.token_count,
        "source_count": result.source_count,
        "confidence": result.confidence,
        "created_at": result.created_at.isoformat()
    }


async def summarize_documents(documents: List[Dict[str, Any]], summary_type: str = "detailed") -> Dict[str, Any]:
    """总结多个文档（对外接口）"""
    try:
        summary_type_enum = SummaryType[summary_type.upper()]
    except KeyError:
        summary_type_enum = SummaryType.DETAILED

    result = await summary_chain.summarize_documents(documents, summary_type_enum)
    
    return {
        "content": result.content,
        "type": result.type.value,
        "token_count": result.token_count,
        "source_count": result.source_count,
        "confidence": result.confidence,
        "created_at": result.created_at.isoformat()
    }


async def summarize_conversation(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """总结对话历史（对外接口）"""
    result = await summary_chain.summarize_conversation(messages)
    
    return {
        "content": result.content,
        "type": result.type.value,
        "token_count": result.token_count,
        "source_count": result.source_count,
        "confidence": result.confidence,
        "created_at": result.created_at.isoformat()
    }


async def extract_key_points(content: str, max_points: int = 10) -> List[str]:
    """提取关键要点（对外接口）"""
    return await summary_chain.extract_key_points(content, max_points)


async def generate_title(content: str, max_length: int = 50) -> str:
    """生成标题（对外接口）"""
    return await summary_chain.generate_title(content, max_length)