"""文档总结生成器
支持多种总结策略：抽取式、生成式、关键点提取
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from backend.chain.rag_chain import get_rag_chain
from backend.prompt import default_prompts
from backend.utils.logger import get_logger
from backend.utils.performance import timed_operation

logger = get_logger(__name__)


class SummaryType(str, Enum):
    """总结类型"""

    BRIEF = "brief"
    DETAILED = "detailed"
    KEY_POINTS = "key_points"
    FULL = "full"


class SummaryGenerator:
    """文档总结生成器"""

    def __init__(self):
        self.rag_chain = get_rag_chain()

    def generate_summary(
        self,
        document: str,
        summary_type: SummaryType = SummaryType.BRIEF,
        max_length: int = 500,
    ) -> str:
        """生成文档总结"""
        with timed_operation("generate_summary"):
            prompt = self._build_summary_prompt(document, summary_type, max_length)
            summary = self.rag_chain.generate(prompt)

            logger.info(f"文档总结生成完成: type={summary_type}, length={len(summary)}")
            return summary

    async def async_generate_summary(
        self,
        document: str,
        summary_type: SummaryType = SummaryType.BRIEF,
        max_length: int = 500,
    ) -> str:
        """异步生成文档总结"""
        with timed_operation("async_generate_summary"):
            prompt = self._build_summary_prompt(document, summary_type, max_length)
            summary = await self.rag_chain.async_generate(prompt)

            logger.info(f"文档总结生成完成: type={summary_type}, length={len(summary)}")
            return summary

    def _build_summary_prompt(
        self, document: str, summary_type: SummaryType, max_length: int
    ) -> str:
        """构建总结提示词"""
        if summary_type == SummaryType.BRIEF:
            return default_prompts.format(
                "summary_brief",
                document=document[:8000],
                max_length=max_length,
            )
        elif summary_type == SummaryType.DETAILED:
            return default_prompts.format(
                "summary_detailed",
                document=document[:8000],
            )
        elif summary_type == SummaryType.KEY_POINTS:
            return default_prompts.format(
                "summary_key_points",
                document=document[:8000],
            )
        else:
            return default_prompts.format(
                "summary_full",
                document=document[:8000],
            )

    def extract_key_points(self, document: str, max_points: int = 10) -> List[str]:
        """提取关键要点"""
        with timed_operation("extract_key_points"):
            prompt = default_prompts.format(
                "extract_key_points",
                document=document[:8000],
                max_points=max_points,
            )

            key_points_text = self.rag_chain.generate(prompt)

            key_points = [
                line.strip()
                for line in key_points_text.split("\n")
                if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))
            ]

            logger.info(f"关键要点提取完成: {len(key_points)} 个要点")
            return key_points

    async def async_extract_key_points(
        self, document: str, max_points: int = 10
    ) -> List[str]:
        """异步提取关键要点"""
        with timed_operation("async_extract_key_points"):
            prompt = default_prompts.format(
                "extract_key_points",
                document=document[:8000],
                max_points=max_points,
            )

            key_points_text = await self.rag_chain.async_generate(prompt)

            key_points = [
                line.strip()
                for line in key_points_text.split("\n")
                if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))
            ]

            logger.info(f"关键要点提取完成: {len(key_points)} 个要点")
            return key_points

    def generate_multi_level_summary(
        self, document: str
    ) -> Dict[str, Any]:
        """生成多层级总结"""
        with timed_operation("generate_multi_level_summary"):
            brief = self.generate_summary(document, SummaryType.BRIEF, 200)
            detailed = self.generate_summary(document, SummaryType.DETAILED, 1000)
            key_points = self.extract_key_points(document, 10)

            result = {
                "brief_summary": brief,
                "detailed_summary": detailed,
                "key_points": key_points,
                "word_count": len(document),
                "estimated_read_time": len(document) // 1000,
            }

            logger.info("多层级总结生成完成")
            return result

    async def async_generate_multi_level_summary(
        self, document: str
    ) -> Dict[str, Any]:
        """异步生成多层级总结"""
        with timed_operation("async_generate_multi_level_summary"):
            brief = await self.async_generate_summary(document, SummaryType.BRIEF, 200)
            detailed = await self.async_generate_summary(document, SummaryType.DETAILED, 1000)
            key_points = await self.async_extract_key_points(document, 10)

            result = {
                "brief_summary": brief,
                "detailed_summary": detailed,
                "key_points": key_points,
                "word_count": len(document),
                "estimated_read_time": len(document) // 1000,
            }

            logger.info("多层级总结生成完成")
            return result

    def summarize_chapters(self, document: str) -> List[Dict[str, str]]:
        """总结文档各章节"""
        with timed_operation("summarize_chapters"):
            prompt = default_prompts.format(
                "summarize_chapters",
                document=document[:10000],
            )

            result = self.rag_chain.generate(prompt)

            chapters = []
            current_chapter = {}

            for line in result.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("第") and "章" in line:
                    if current_chapter:
                        chapters.append(current_chapter)
                    current_chapter = {"title": line, "summary": ""}
                elif current_chapter:
                    current_chapter["summary"] += line + " "

            if current_chapter:
                chapters.append(current_chapter)

            logger.info(f"章节总结完成: {len(chapters)} 个章节")
            return chapters

    def compare_documents(
        self, document1: str, document2: str
    ) -> Dict[str, Any]:
        """对比两个文档"""
        with timed_operation("compare_documents"):
            prompt = default_prompts.format(
                "compare_documents",
                document1=document1[:4000],
                document2=document2[:4000],
            )

            comparison = self.rag_chain.generate(prompt)

            return {
                "comparison": comparison,
                "doc1_length": len(document1),
                "doc2_length": len(document2),
            }

    def generate_timeline(self, document: str) -> List[Dict[str, str]]:
        """从文档中提取时间线"""
        with timed_operation("generate_timeline"):
            prompt = default_prompts.format(
                "extract_timeline",
                document=document[:8000],
            )

            result = self.rag_chain.generate(prompt)

            timeline = []
            for line in result.split("\n"):
                line = line.strip()
                if line and ("：" in line or "-" in line):
                    parts = line.split(":", 1)
                    if len(parts) == 1:
                        parts = line.split("-", 1)
                    if len(parts) == 2:
                        timeline.append(
                            {
                                "time": parts[0].strip(),
                                "event": parts[1].strip(),
                            }
                        )

            logger.info(f"时间线提取完成: {len(timeline)} 个事件")
            return timeline


_summary_generator: Optional[SummaryGenerator] = None


def get_summary_generator() -> SummaryGenerator:
    """获取总结生成器实例"""
    global _summary_generator
    if _summary_generator is None:
        _summary_generator = SummaryGenerator()
        logger.info("文档总结生成器已初始化")
    return _summary_generator
