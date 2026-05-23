"""实体抽取模块 - 使用 SpaCy 进行命名实体识别"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    spacy = None
    SPACY_AVAILABLE = False
    logger.warning("SpaCy 未安装，将使用基于规则的实体抽取")


class Entity(BaseModel):
    """实体模型"""

    text: str = Field(..., description="实体文本")
    label: str = Field(..., description="实体类型")
    start: int = Field(..., description="起始位置")
    end: int = Field(..., description="结束位置")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="额外元数据")


class NERExtractor:
    """命名实体识别抽取器

    使用 SpaCy 进行实体识别，支持中文和英文，
    提供自定义实体类型扩展能力。
    当 SpaCy 不可用时，自动降级到基于规则的实体抽取。
    """

    def __init__(self, model_name: str = "zh_core_web_sm"):
        """初始化 NER 抽取器

        Args:
            model_name: SpaCy 模型名称，默认为中文模型
        """
        self.model_name = model_name
        self.nlp = self._load_model()
        self.custom_entity_types = self._init_custom_entity_types()

    def _load_model(self) -> Any:
        """加载 SpaCy 模型，失败时返回 None"""
        if not SPACY_AVAILABLE:
            logger.warning("SpaCy 不可用，将使用基于规则的实体抽取")
            return None

        try:
            return spacy.load(self.model_name)
        except OSError:
            logger.warning(f"模型 {self.model_name} 未找到，将使用基于规则的实体抽取")
            return None

    def _init_custom_entity_types(self) -> Dict[str, str]:
        """初始化自定义实体类型映射"""
        return {
            "PRODUCT": "产品",
            "EVENT": "事件",
            "WORK_OF_ART": "艺术作品",
            "LAW": "法律",
            "LANGUAGE": "语言",
            "DATE": "日期",
            "TIME": "时间",
            "PERCENT": "百分比",
            "MONEY": "货币",
            "QUANTITY": "数量",
            "ORDINAL": "序数",
            "CARDINAL": "基数",
        }

    def extract_entities(self, text: str, entities_filter: Optional[List[str]] = None) -> List[Entity]:
        """从文本中抽取实体

        Args:
            text: 输入文本
            entities_filter: 实体类型过滤器，如果指定则只返回这些类型的实体

        Returns:
            实体列表
        """
        if not text or not text.strip():
            return []

        if self.nlp is None:
            return self._rule_based_extract(text, entities_filter)

        try:
            doc = self.nlp(text)
            entities = []

            for ent in doc.ents:
                if entities_filter and ent.label_ not in entities_filter:
                    continue

                entity = Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0,
                    metadata={"source": "spacy"},
                )
                entities.append(entity)

            logger.info(f"从文本中抽取了 {len(entities)} 个实体")
            return entities

        except Exception as e:
            logger.error(f"实体抽取失败: {str(e)}")
            return self._rule_based_extract(text, entities_filter)

    def _rule_based_extract(self, text: str, entities_filter: Optional[List[str]] = None) -> List[Entity]:
        """基于规则的实体抽取（降级方案）

        Args:
            text: 输入文本
            entities_filter: 实体类型过滤器

        Returns:
            实体列表
        """
        import re

        entities = []
        seen_entities = set()

        patterns = [
            # 日期时间模式
            (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "DATE"),
            (r"\d{1,2}:\d{2}(:\d{2})?", "TIME"),
            (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "DATE"),
            (r"(\d{4})年(\d{1,2})月", "DATE"),
            (r"(\d{1,2})月(\d{1,2})日", "DATE"),
            (r"\d{4}年", "DATE"),
            (r"成立于(\d{4})年", "DATE"),
            (r"创立于(\d{4})年", "DATE"),
            (r"(\d{4})年成立", "DATE"),
            (r"(\d{4})年创立", "DATE"),
            (r"(\d{4})年发布", "DATE"),
            (r"(\d{4})年推出", "DATE"),
            (r"(\d{4})年上市", "DATE"),
            # 百分比和数字
            (r"\d+(\.\d+)?%", "PERCENT"),
            (r"(\d+)亿", "MONEY"),
            (r"(\d+)万", "MONEY"),
            (r"(\d+)元", "MONEY"),
            (r"(\d+)美元", "MONEY"),
            (r"(\d+)欧元", "MONEY"),
            (r"\d+(\.\d+)?元", "MONEY"),
            (r"\d+(\.\d+)?亿美元", "MONEY"),
            (r"\d+(\.\d+)?亿元", "MONEY"),
            (r"(\d+)%以上", "PERCENT"),
            (r"(\d+)%以下", "PERCENT"),
            # 组织实体
            (r"[\u4e00-\u9fa5]+公司", "ORG"),
            (r"[\u4e00-\u9fa5]+集团", "ORG"),
            (r"[\u4e00-\u9fa5]+科技", "ORG"),
            (r"[\u4e00-\u9fa5]+股份", "ORG"),
            (r"[\u4e00-\u9fa5]+有限", "ORG"),
            (r"[\u4e00-\u9fa5]+股份有限公司", "ORG"),
            (r"[\u4e00-\u9fa5]+有限公司", "ORG"),
            (r"[\u4e00-\u9fa5]+科技有限公司", "ORG"),
            (r"[\u4e00-\u9fa5]+技术有限公司", "ORG"),
            (r"[\u4e00-\u9fa5]+互联网", "ORG"),
            (r"[\u4e00-\u9fa5]+网络", "ORG"),
            (r"[\u4e00-\u9fa5]+软件", "ORG"),
            (r"[\u4e00-\u9fa5]+数据", "ORG"),
            (r"[\u4e00-\u9fa5]+智能", "ORG"),
            (r"[\u4e00-\u9fa5]+人工智能", "ORG"),
            (r"[\u4e00-\u9fa5]+研究院", "ORG"),
            (r"[\u4e00-\u9fa5]+研究所", "ORG"),
            (r"[\u4e00-\u9fa5]+大学", "ORG"),
            (r"[\u4e00-\u9fa5]+学院", "ORG"),
            (r"[\u4e00-\u9fa5]+中学", "ORG"),
            (r"[\u4e00-\u9fa5]+小学", "ORG"),
            (r"[\u4e00-\u9fa5]+医院", "ORG"),
            (r"[\u4e00-\u9fa5]+银行", "ORG"),
            (r"[\u4e00-\u9fa5]+基金", "ORG"),
            (r"[\u4e00-\u9fa5]+保险", "ORG"),
            (r"[\u4e00-\u9fa5]+证券", "ORG"),
            (r"[\u4e00-\u9fa5]+集团公司", "ORG"),
            # 地理实体 - 国家
            (r"美国", "GPE"),
            (r"中国", "GPE"),
            (r"日本", "GPE"),
            (r"韩国", "GPE"),
            (r"英国", "GPE"),
            (r"法国", "GPE"),
            (r"德国", "GPE"),
            (r"加拿大", "GPE"),
            (r"澳大利亚", "GPE"),
            (r"新加坡", "GPE"),
            (r"马来西亚", "GPE"),
            (r"印度", "GPE"),
            (r"俄罗斯", "GPE"),
            (r"泰国", "GPE"),
            (r"越南", "GPE"),
            (r"印度尼西亚", "GPE"),
            (r"菲律宾", "GPE"),
            (r"意大利", "GPE"),
            (r"西班牙", "GPE"),
            (r"葡萄牙", "GPE"),
            (r"荷兰", "GPE"),
            (r"瑞士", "GPE"),
            (r"瑞典", "GPE"),
            (r"挪威", "GPE"),
            (r"丹麦", "GPE"),
            (r"芬兰", "GPE"),
            (r"爱尔兰", "GPE"),
            (r"新西兰", "GPE"),
            (r"巴西", "GPE"),
            (r"阿根廷", "GPE"),
            (r"墨西哥", "GPE"),
            (r"南非", "GPE"),
            # 地理实体 - 中国省份
            (r"北京市", "GPE"),
            (r"上海市", "GPE"),
            (r"广州市", "GPE"),
            (r"深圳市", "GPE"),
            (r"杭州市", "GPE"),
            (r"南京市", "GPE"),
            (r"武汉市", "GPE"),
            (r"成都市", "GPE"),
            (r"重庆市", "GPE"),
            (r"天津市", "GPE"),
            (r"苏州市", "GPE"),
            (r"西安市", "GPE"),
            (r"郑州市", "GPE"),
            (r"长沙市", "GPE"),
            (r"沈阳市", "GPE"),
            (r"青岛市", "GPE"),
            (r"宁波市", "GPE"),
            (r"厦门市", "GPE"),
            (r"大连市", "GPE"),
            (r"无锡市", "GPE"),
            (r"佛山市", "GPE"),
            (r"东莞市", "GPE"),
            (r"珠海市", "GPE"),
            (r"中山市", "GPE"),
            (r"江苏省", "GPE"),
            (r"浙江省", "GPE"),
            (r"广东省", "GPE"),
            (r"山东省", "GPE"),
            (r"四川省", "GPE"),
            (r"湖北省", "GPE"),
            (r"湖南省", "GPE"),
            (r"河南省", "GPE"),
            (r"河北省", "GPE"),
            (r"安徽省", "GPE"),
            (r"福建省", "GPE"),
            (r"江西省", "GPE"),
            (r"山西省", "GPE"),
            (r"陕西省", "GPE"),
            (r"辽宁省", "GPE"),
            (r"吉林省", "GPE"),
            (r"黑龙江省", "GPE"),
            (r"云南省", "GPE"),
            (r"贵州省", "GPE"),
            (r"广西壮族自治区", "GPE"),
            (r"西藏自治区", "GPE"),
            (r"新疆维吾尔自治区", "GPE"),
            (r"内蒙古自治区", "GPE"),
            (r"宁夏回族自治区", "GPE"),
            (r"海南省", "GPE"),
            (r"台湾省", "GPE"),
            (r"香港特别行政区", "GPE"),
            (r"澳门特别行政区", "GPE"),
            # 地理实体 - 常用城市别称
            (r"北京", "GPE"),
            (r"上海", "GPE"),
            (r"深圳", "GPE"),
            (r"杭州", "GPE"),
            (r"广州", "GPE"),
            (r"成都", "GPE"),
            (r"武汉", "GPE"),
            (r"南京", "GPE"),
            (r"苏州", "GPE"),
            (r"西安", "GPE"),
            (r"重庆", "GPE"),
            (r"天津", "GPE"),
            (r"郑州", "GPE"),
            (r"长沙", "GPE"),
            (r"沈阳", "GPE"),
            (r"青岛", "GPE"),
            (r"宁波", "GPE"),
            (r"厦门", "GPE"),
            (r"大连", "GPE"),
            (r"无锡", "GPE"),
            (r"佛山", "GPE"),
            (r"东莞", "GPE"),
            # 人物实体
            (r"[\u4e00-\u9fa5]{2,4}创始人", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}CEO", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}董事长", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}总裁", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}总经理", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}首席执行官", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}首席技术官", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}CTO", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}COO", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}CFO", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}副总裁", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}总监", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}经理", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}博士", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}教授", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}研究员", "PERSON"),
            (r"[\u4e00-\u9fa5]{2,4}院士", "PERSON"),
            (r"([\u4e00-\u9fa5]{2,4})是创始人", "PERSON"),
            (r"([\u4e00-\u9fa5]{2,4})是创始人之一", "PERSON"),
            (r"([\u4e00-\u9fa5]{2,4})创立了", "PERSON"),
            (r"由([\u4e00-\u9fa5]{2,4})创立", "PERSON"),
            (r"乔布斯", "PERSON"),
            (r"比尔·盖茨", "PERSON"),
            (r"马斯克", "PERSON"),
            (r"马云", "PERSON"),
            (r"马化腾", "PERSON"),
            (r"李彦宏", "PERSON"),
            (r"雷军", "PERSON"),
            (r"任正非", "PERSON"),
            (r"董明珠", "PERSON"),
            (r"王健林", "PERSON"),
            (r"许家印", "PERSON"),
            (r"丁磊", "PERSON"),
            (r"张一鸣", "PERSON"),
            (r"黄峥", "PERSON"),
            (r"刘强东", "PERSON"),
            (r"俞敏洪", "PERSON"),
            (r"周鸿祎", "PERSON"),
            (r"李开复", "PERSON"),
            (r"沈南鹏", "PERSON"),
            (r"孙正义", "PERSON"),
            (r"巴菲特", "PERSON"),
            (r"查理·芒格", "PERSON"),
            # 产品实体
            (r"iPhone[\s\S]*", "PRODUCT"),
            (r"iPad[\s\S]*", "PRODUCT"),
            (r"Mac[\s\S]*", "PRODUCT"),
            (r"华为[\s\S]*", "PRODUCT"),
            (r"小米[\s\S]*", "PRODUCT"),
            (r"OPPO[\s\S]*", "PRODUCT"),
            (r"vivo[\s\S]*", "PRODUCT"),
            (r"荣耀[\s\S]*", "PRODUCT"),
            (r"联想[\s\S]*", "PRODUCT"),
            (r"戴尔[\s\S]*", "PRODUCT"),
            (r"华硕[\s\S]*", "PRODUCT"),
            (r"三星[\s\S]*", "PRODUCT"),
            (r"索尼[\s\S]*", "PRODUCT"),
            (r"微软[\s\S]*", "PRODUCT"),
            (r"Windows[\s\S]*", "PRODUCT"),
            (r"Office[\s\S]*", "PRODUCT"),
            (r"微信", "PRODUCT"),
            (r"支付宝", "PRODUCT"),
            (r"淘宝", "PRODUCT"),
            (r"天猫", "PRODUCT"),
            (r"京东", "PRODUCT"),
            (r"拼多多", "PRODUCT"),
            (r"抖音", "PRODUCT"),
            (r"快手", "PRODUCT"),
            (r"美团", "PRODUCT"),
            (r"滴滴", "PRODUCT"),
            (r"小红书", "PRODUCT"),
            (r"微博", "PRODUCT"),
            (r"B站", "PRODUCT"),
            (r"知乎", "PRODUCT"),
            (r"百度", "PRODUCT"),
            (r"搜索引擎", "PRODUCT"),
            (r"人工智能模型", "PRODUCT"),
            (r"大语言模型", "PRODUCT"),
            # 技术术语
            (r"人工智能", "TECHNOLOGY"),
            (r"机器学习", "TECHNOLOGY"),
            (r"深度学习", "TECHNOLOGY"),
            (r"神经网络", "TECHNOLOGY"),
            (r"自然语言处理", "TECHNOLOGY"),
            (r"NLP", "TECHNOLOGY"),
            (r"计算机视觉", "TECHNOLOGY"),
            (r"CV", "TECHNOLOGY"),
            (r"RAG", "TECHNOLOGY"),
            (r"检索增强生成", "TECHNOLOGY"),
            (r"LLM", "TECHNOLOGY"),
            (r"大语言模型", "TECHNOLOGY"),
            (r"GPT", "TECHNOLOGY"),
            (r"Transformer", "TECHNOLOGY"),
            (r"向量数据库", "TECHNOLOGY"),
            (r"知识图谱", "TECHNOLOGY"),
            (r"云计算", "TECHNOLOGY"),
            (r"大数据", "TECHNOLOGY"),
            (r"区块链", "TECHNOLOGY"),
            (r"元宇宙", "TECHNOLOGY"),
            (r"物联网", "TECHNOLOGY"),
            (r"IoT", "TECHNOLOGY"),
            (r"边缘计算", "TECHNOLOGY"),
            (r"量子计算", "TECHNOLOGY"),
            (r"5G", "TECHNOLOGY"),
            (r"6G", "TECHNOLOGY"),
            (r"API", "TECHNOLOGY"),
            (r"REST", "TECHNOLOGY"),
            (r"GraphQL", "TECHNOLOGY"),
            (r"微服务", "TECHNOLOGY"),
            (r"容器化", "TECHNOLOGY"),
            (r"Docker", "TECHNOLOGY"),
            (r"Kubernetes", "TECHNOLOGY"),
            (r"K8s", "TECHNOLOGY"),
            (r"CI/CD", "TECHNOLOGY"),
            (r"DevOps", "TECHNOLOGY"),
        ]

        for pattern, label in patterns:
            if entities_filter and label not in entities_filter:
                continue

            matches = list(re.finditer(pattern, text))
            for match in matches:
                text_content = match.group()
                if len(text_content) == 1:
                    continue

                key = (text_content, label, match.start())
                if key in seen_entities:
                    continue
                seen_entities.add(key)

                entity = Entity(
                    text=text_content,
                    label=label,
                    start=match.start(),
                    end=match.start() + len(text_content),
                    confidence=0.7,
                    metadata={"source": "rule_based"},
                )
                entities.append(entity)

        logger.info(f"基于规则抽取了 {len(entities)} 个实体")
        return entities

    def extract_with_custom_types(
        self, text: str, custom_patterns: Optional[Dict[str, List[Dict]]] = None
    ) -> List[Entity]:
        """使用自定义模式抽取实体

        Args:
            text: 输入文本
            custom_patterns: 自定义实体模式，格式为 {entity_type: [{pattern: ...}]}

        Returns:
            实体列表
        """
        entities = self.extract_entities(text)

        if custom_patterns:
            import re

            for entity_type, patterns in custom_patterns.items():
                for pattern_config in patterns:
                    pattern = pattern_config.get("pattern")
                    if pattern:
                        for match in re.finditer(pattern, text):
                            entity = Entity(
                                text=match.group(),
                                label=entity_type,
                                start=match.start(),
                                end=match.end(),
                                confidence=0.9,
                                metadata={"source": "custom_pattern"},
                            )
                            entities.append(entity)

        return entities

    def get_entity_types(self) -> List[str]:
        """获取所有可用的实体类型

        Returns:
            实体类型列表
        """
        if hasattr(self.nlp, "pipe_labels"):
            return list(self.nlp.pipe_labels.get("ner", []))
        return []

    def batch_extract(self, texts: List[str], entities_filter: Optional[List[str]] = None) -> List[List[Entity]]:
        """批量抽取实体

        Args:
            texts: 文本列表
            entities_filter: 实体类型过滤器

        Returns:
            每个文本对应的实体列表
        """
        if not texts:
            return []

        if self.nlp is None:
            return [self._rule_based_extract(text, entities_filter) for text in texts]

        try:
            results = []
            for doc in self.nlp.pipe(texts):
                entities = []
                for ent in doc.ents:
                    if entities_filter and ent.label_ not in entities_filter:
                        continue

                    entity = Entity(
                        text=ent.text,
                        label=ent.label_,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=1.0,
                        metadata={"source": "spacy"},
                    )
                    entities.append(entity)
                results.append(entities)

            logger.info(f"批量抽取完成，共处理 {len(texts)} 个文本")
            return results

        except Exception as e:
            logger.error(f"批量实体抽取失败: {str(e)}")
            return [self._rule_based_extract(text, entities_filter) for text in texts]

    def add_custom_entity_ruler(self, patterns: List[Dict[str, str]]):
        """添加自定义实体规则

        Args:
            patterns: 实体模式列表，格式为 [{"label": "PRODUCT", "pattern": "产品名称"}]
        """
        try:
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            ruler.add_patterns(patterns)
            logger.info(f"添加了 {len(patterns)} 个自定义实体模式")
        except Exception as e:
            logger.error(f"添加自定义实体规则失败: {str(e)}")

    def get_entity_stats(self, entities: List[Entity]) -> Dict[str, int]:
        """获取实体统计信息

        Args:
            entities: 实体列表

        Returns:
            实体类型统计字典
        """
        stats = {}
        for entity in entities:
            stats[entity.label] = stats.get(entity.label, 0) + 1
        return stats
