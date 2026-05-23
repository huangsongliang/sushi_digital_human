"""关系抽取模块 - 基于规则和 LLM 的关系抽取"""

import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.generator import get_async_llm
from backend.knowledge_graph.ner_extractor import Entity
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class Relation(BaseModel):
    """关系模型"""

    source: str = Field(..., description="源实体文本")
    source_type: str = Field(..., description="源实体类型")
    target: str = Field(..., description="目标实体文本")
    target_type: str = Field(..., description="目标实体类型")
    relation_type: str = Field(..., description="关系类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    context: Optional[str] = Field(default=None, description="关系上下文")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="额外元数据")


class RelationExtractor:
    """关系抽取器

    结合基于规则的方法和 LLM 进行关系抽取，
    支持自定义关系类型和规则配置。
    """

    def __init__(self):
        """初始化关系抽取器"""
        self.rule_patterns = self._init_rule_patterns()
        self.relation_templates = self._init_relation_templates()

    def _init_rule_patterns(self) -> Dict[str, List[str]]:
        """初始化基于规则的关系模式"""
        return {
            "工作于": [
                r"(.+?)(在|于|就职于|工作于|任职于)(.+?)(公司|企业|机构|组织)",
                r"(.+?)是(.+?)(公司|企业|机构|组织)的(.+?)",
            ],
            "位于": [
                r"(.+?)位于(.+?)(城市|国家|地区|省|市|县)",
                r"(.+?)坐落于(.+?)",
            ],
            "创作": [
                r"(.+?)(创作|编写|著|著作|编写了)(.+?)",
                r"(.+?)是(.+?)(著|编写|创作)的",
            ],
            "属于": [
                r"(.+?)(属于|是.+的一部分)",
                r"(.+?)隶属于(.+?)",
            ],
            "合作": [
                r"(.+?)(与|和)(.+?)(合作|协作|搭档|共同)",
                r"(.+?)与(.+?)(合作|协作)",
            ],
            "研发": [
                r"(.+?)(研发|开发|研制|设计了)(.+?)",
                r"(.+?)由(.+?)研发",
            ],
            "发布": [
                r"(.+?)(发布|推出|推出)(.+?)",
                r"(.+?)于(.+?)(发布|推出)",
            ],
            "使用": [
                r"(.+?)(使用|采用|运用)(.+?)",
                r"(.+?)基于(.+?)",
            ],
        }

    def _init_relation_templates(self) -> Dict[str, str]:
        """初始化关系模板，用于 LLM 关系抽取"""
        return {
            "prompt": """从以下文本中抽取实体之间的关系。

文本: {text}

已识别的实体:
{entities}

请以 JSON 格式返回关系列表，格式如下:
{{
    "relations": [
        {{
            "source": "源实体",
            "source_type": "源实体类型",
            "target": "目标实体",
            "target_type": "目标实体类型",
            "relation_type": "关系类型",
            "confidence": 0.9,
            "context": "关系所在上下文"
        }}
    ]
}}

关系类型包括: 工作于、位于、创作、属于、合作、研发、发布、使用等。
如果文本中不存在明显的关系，返回空列表。
只返回 JSON，不要包含其他解释性文本。""",
        }

    def extract_relations_with_rules(self, text: str, entities: List[Entity]) -> List[Relation]:
        """使用规则方法抽取关系

        Args:
            text: 输入文本
            entities: 实体列表

        Returns:
            关系列表
        """
        if not text or not entities:
            return []

        relations = []
        entity_texts = [e.text for e in entities]

        for relation_type, patterns in self.rule_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        source = groups[0].strip()
                        target = groups[-1].strip()

                        if source in entity_texts and target in entity_texts:
                            source_entity = next((e for e in entities if e.text == source), None)
                            target_entity = next((e for e in entities if e.text == target), None)

                            if source_entity and target_entity:
                                relation = Relation(
                                    source=source,
                                    source_type=source_entity.label,
                                    target=target,
                                    target_type=target_entity.label,
                                    relation_type=relation_type,
                                    confidence=0.85,
                                    context=match.group(),
                                    metadata={"source": "rule_based"},
                                )
                                relations.append(relation)

        logger.info(f"规则抽取找到 {len(relations)} 个关系")
        return relations

    async def extract_relations_with_llm(self, text: str, entities: List[Entity]) -> List[Relation]:
        """使用 LLM 抽取关系

        Args:
            text: 输入文本
            entities: 实体列表

        Returns:
            关系列表
        """
        if not text or not entities:
            return []

        try:
            prompt = self.relation_templates["prompt"].format(
                text=text, entities="\n".join([f"- {e.text} ({e.label})" for e in entities])
            )

            llm = get_async_llm()
            response = await llm.async_generate(prompt, temperature=0.3)

            relations = self._parse_llm_response(response, text, entities)
            logger.info(f"LLM 抽取找到 {len(relations)} 个关系")
            return relations

        except Exception as e:
            logger.error(f"LLM 关系抽取失败: {str(e)}")
            return []

    def _parse_llm_response(
        self, response: str, original_text: str, entities: List[Entity]
    ) -> List[Relation]:
        """解析 LLM 返回的关系

        Args:
            response: LLM 响应
            original_text: 原始文本
            entities: 实体列表

        Returns:
            关系列表
        """
        relations = []

        try:
            import json

            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                relation_list = data.get("relations", [])

                for rel_data in relation_list:
                    source_text = rel_data.get("source", "")
                    target_text = rel_data.get("target", "")

                    source_entity = next((e for e in entities if e.text == source_text), None)
                    target_entity = next((e for e in entities if e.text == target_text), None)

                    if source_entity and target_entity:
                        relation = Relation(
                            source=source_text,
                            source_type=rel_data.get("source_type", source_entity.label),
                            target=target_text,
                            target_type=rel_data.get("target_type", target_entity.label),
                            relation_type=rel_data.get("relation_type", "相关"),
                            confidence=rel_data.get("confidence", 0.8),
                            context=rel_data.get("context"),
                            metadata={"source": "llm_based"},
                        )
                        relations.append(relation)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析 LLM 响应失败: {str(e)}")

        return relations

    async def extract_relations_hybrid(
        self, text: str, entities: List[Entity], use_llm: bool = True
    ) -> List[Relation]:
        """混合方法抽取关系

        先使用规则抽取，再使用 LLM 补充

        Args:
            text: 输入文本
            entities: 实体列表
            use_llm: 是否使用 LLM

        Returns:
            关系列表
        """
        rule_relations = self.extract_relations_with_rules(text, entities)

        if use_llm:
            llm_relations = await self.extract_relations_with_llm(text, entities)

            existing_relations = set()
            for rel in rule_relations:
                key = (rel.source, rel.target, rel.relation_type)
                existing_relations.add(key)

            for rel in llm_relations:
                key = (rel.source, rel.target, rel.relation_type)
                if key not in existing_relations:
                    rule_relations.append(rel)

        return rule_relations

    def get_relation_types(self) -> List[str]:
        """获取所有关系类型

        Returns:
            关系类型列表
        """
        return list(self.rule_patterns.keys())

    def add_custom_relation_pattern(self, relation_type: str, patterns: List[str]):
        """添加自定义关系模式

        Args:
            relation_type: 关系类型
            patterns: 正则表达式模式列表
        """
        if relation_type in self.rule_patterns:
            self.rule_patterns[relation_type].extend(patterns)
        else:
            self.rule_patterns[relation_type] = patterns

        logger.info(f"为关系类型 '{relation_type}' 添加了 {len(patterns)} 个模式")

    def batch_extract_relations(
        self, texts: List[str], entities_list: List[List[Entity]], use_llm: bool = False
    ) -> List[List[Relation]]:
        """批量抽取关系

        Args:
            texts: 文本列表
            entities_list: 实体列表列表
            use_llm: 是否使用 LLM

        Returns:
            每个文本对应的关系列表
        """
        if len(texts) != len(entities_list):
            logger.error("文本数量和实体列表数量不匹配")
            return []

        results = []
        for text, entities in zip(texts, entities_list):
            if use_llm:
                import asyncio

                relations = asyncio.run(self.extract_relations_hybrid(text, entities, use_llm=False))
            else:
                relations = self.extract_relations_with_rules(text, entities)
            results.append(relations)

        logger.info(f"批量关系抽取完成，共处理 {len(texts)} 个文本")
        return results
