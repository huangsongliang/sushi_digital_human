"""知识图谱 API 路由"""

import traceback
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.knowledge_graph import (
    Edge,
    Entity,
    GraphQuery,
    GraphStorage,
    NERExtractor,
    Node,
    Relation,
    RelationExtractor,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/kg", tags=["knowledge_graph"])

_storage: Optional[GraphStorage] = None
_ner_extractor: Optional[NERExtractor] = None
_relation_extractor: Optional[RelationExtractor] = None
_graph_query: Optional[GraphQuery] = None


def get_storage() -> GraphStorage:
    """获取图谱存储实例"""
    global _storage
    if _storage is None:
        _storage = GraphStorage()
    return _storage


def get_ner_extractor() -> NERExtractor:
    """获取 NER 抽取器实例"""
    global _ner_extractor
    if _ner_extractor is None:
        _ner_extractor = NERExtractor()
    return _ner_extractor


def get_relation_extractor() -> RelationExtractor:
    """获取关系抽取器实例"""
    global _relation_extractor
    if _relation_extractor is None:
        _relation_extractor = RelationExtractor()
    return _relation_extractor


def get_graph_query() -> GraphQuery:
    """获取图谱查询实例"""
    global _graph_query
    if _graph_query is None:
        _graph_query = GraphQuery(get_storage())
    return _graph_query


class EntityExtractRequest(BaseModel):
    """实体抽取请求模型"""

    text: str = Field(..., min_length=1, max_length=10000, description="待抽取实体的文本")
    entities_filter: Optional[List[str]] = Field(default=None, description="实体类型过滤器")


class EntityExtractResponse(BaseModel):
    """实体抽取响应模型"""

    entities: List[Entity] = Field(..., description="抽取到的实体列表")
    count: int = Field(..., description="实体数量")
    stats: Dict[str, int] = Field(..., description="实体类型统计")


class RelationExtractRequest(BaseModel):
    """关系抽取请求模型"""

    text: str = Field(..., min_length=1, max_length=10000, description="待抽取关系的文本")
    entities: List[Entity] = Field(..., description="已抽取的实体列表")
    use_llm: bool = Field(default=False, description="是否使用 LLM 进行关系抽取")


class RelationExtractResponse(BaseModel):
    """关系抽取响应模型"""

    relations: List[Relation] = Field(..., description="抽取到的关系列表")
    count: int = Field(..., description="关系数量")


class AddNodeRequest(BaseModel):
    """添加节点请求模型"""

    label: str = Field(..., min_length=1, description="节点标签")
    properties: Dict[str, str] = Field(default_factory=dict, description="节点属性")


class AddEdgeRequest(BaseModel):
    """添加边请求模型"""

    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    relation_type: str = Field(..., min_length=1, description="关系类型")
    properties: Dict[str, str] = Field(default_factory=dict, description="边属性")


class AddEntitiesRelationsRequest(BaseModel):
    """添加实体和关系请求模型"""

    entities: List[Entity] = Field(..., description="实体列表")
    relations: List[Relation] = Field(..., description="关系列表")


class QueryRequest(BaseModel):
    """图谱查询请求模型"""

    query: str = Field(..., min_length=1, description="查询关键词")
    entity_ids: Optional[List[str]] = Field(default=None, description="相关实体 ID")
    max_results: int = Field(default=10, ge=1, le=100, description="最大返回结果数")


class NeighborsRequest(BaseModel):
    """邻居查询请求模型"""

    node_id: str = Field(..., description="节点 ID")
    depth: int = Field(default=1, ge=1, le=5, description="查询深度")
    relation_type: Optional[str] = Field(default=None, description="关系类型过滤")


class PathRequest(BaseModel):
    """路径查询请求模型"""

    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    max_length: int = Field(default=5, ge=1, le=10, description="最大路径长度")


@router.post("/extract", response_model=EntityExtractResponse)
async def extract_entities(request: EntityExtractRequest):
    """实体抽取接口

    从文本中抽取命名实体
    """
    try:
        logger.info(f"收到实体抽取请求: text_length={len(request.text)}, text={request.text[:100]}...")

        extractor = get_ner_extractor()
        entities = extractor.extract_entities(request.text, request.entities_filter)

        stats = extractor.get_entity_stats(entities)

        logger.info(f"实体抽取完成: count={len(entities)}, stats={stats}")

        return EntityExtractResponse(entities=entities, count=len(entities), stats=stats)

    except Exception as e:
        logger.error(f"实体抽取失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"实体抽取失败: {str(e)}")


@router.post("/relations", response_model=RelationExtractResponse)
async def extract_relations(request: RelationExtractRequest):
    """关系抽取接口

    从文本和实体中抽取关系
    """
    try:
        extractor = get_relation_extractor()

        if request.use_llm:
            relations = await extractor.extract_relations_hybrid(request.text, request.entities, use_llm=True)
        else:
            relations = extractor.extract_relations_with_rules(request.text, request.entities)

        return RelationExtractResponse(relations=relations, count=len(relations))

    except Exception as e:
        logger.error(f"关系抽取失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"关系抽取失败: {str(e)}")


@router.post("/add/node")
async def add_node(request: AddNodeRequest):
    """添加节点接口

    向图谱中添加单个节点
    """
    try:
        storage = get_storage()
        node = Node(label=request.label, properties=request.properties)
        node_id = storage.create_node(node)

        if node_id:
            return {"status": "success", "node_id": node_id}
        else:
            raise HTTPException(status_code=500, detail="节点创建失败")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"添加节点失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"添加节点失败: {str(e)}")


@router.post("/add/edge")
async def add_edge(request: AddEdgeRequest):
    """添加边接口

    向图谱中添加单个边
    """
    try:
        storage = get_storage()
        edge = Edge(
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            properties=request.properties,
        )
        success = storage.create_edge(edge)

        if success:
            return {"status": "success", "message": "边创建成功"}
        else:
            raise HTTPException(status_code=500, detail="边创建失败")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"添加边失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"添加边失败: {str(e)}")


@router.post("/add")
async def add_entities_and_relations(request: AddEntitiesRelationsRequest):
    """批量添加实体和关系接口

    一次性添加多个实体和关系
    """
    try:
        storage = get_storage()

        entity_id_map = {}
        for entity in request.entities:
            node = Node(label=entity.label, properties={"text": entity.text, "type": entity.label})
            node_id = storage.create_node(node)
            if node_id:
                entity_id_map[entity.text] = node_id

        success_count = 0
        for relation in request.relations:
            source_id = entity_id_map.get(relation.source)
            target_id = entity_id_map.get(relation.target)

            if source_id and target_id:
                edge = Edge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation.relation_type,
                    properties={"confidence": str(relation.confidence)},
                )
                if storage.create_edge(edge):
                    success_count += 1

        return {
            "status": "success",
            "entities_added": len(entity_id_map),
            "relations_added": success_count,
        }

    except Exception as e:
        logger.error(f"批量添加失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"批量添加失败: {str(e)}")


@router.get("/query")
async def query_graph(query: str, max_results: int = 10):
    """图谱查询接口

    根据关键词查询图谱
    """
    try:
        graph_query = get_graph_query()
        results = graph_query.enhanced_retrieval(query, max_results=max_results)

        return results

    except Exception as e:
        logger.error(f"图谱查询失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"图谱查询失败: {str(e)}")


@router.get("/neighbors/{node_id}")
async def get_neighbors(node_id: str, depth: int = 1, relation_type: Optional[str] = None):
    """邻居查询接口

    获取指定节点的邻居
    """
    try:
        graph_query = get_graph_query()
        neighbors = graph_query.find_neighbors(node_id, depth, relation_type)

        return {"node_id": node_id, "neighbors": neighbors, "total": sum(len(v) for v in neighbors.values())}

    except Exception as e:
        logger.error(f"邻居查询失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"邻居查询失败: {str(e)}")


@router.get("/path/{source_id}/{target_id}")
async def find_path(source_id: str, target_id: str, max_length: int = 5):
    """路径查询接口

    查找两个节点之间的路径
    """
    try:
        graph_query = get_graph_query()
        paths = graph_query.find_path(source_id, target_id, max_length)

        return {"source_id": source_id, "target_id": target_id, "paths": paths, "count": len(paths)}

    except Exception as e:
        logger.error(f"路径查询失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"路径查询失败: {str(e)}")


@router.get("/stats")
async def get_graph_stats():
    """图谱统计接口

    获取图谱的基本统计信息
    """
    try:
        storage = get_storage()
        stats = storage.get_graph_stats()

        return stats

    except Exception as e:
        logger.error(f"获取图谱统计失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取图谱统计失败: {str(e)}")


@router.get("/search")
async def search_nodes(keyword: str, label: Optional[str] = None, limit: int = 10):
    """节点搜索接口

    根据关键词搜索节点
    """
    try:
        graph_query = get_graph_query()
        nodes = graph_query.search_by_text(keyword, label, limit)

        return {"keyword": keyword, "nodes": nodes, "count": len(nodes)}

    except Exception as e:
        logger.error(f"节点搜索失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"节点搜索失败: {str(e)}")


@router.delete("/clear")
async def clear_graph():
    """清空图谱接口

    删除图谱中的所有节点和边
    """
    try:
        storage = get_storage()
        success = storage.clear_graph()

        if success:
            return {"status": "success", "message": "图谱已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空图谱失败")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"清空图谱失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"清空图谱失败: {str(e)}")


@router.get("/entity/types")
async def get_entity_types():
    """获取实体类型接口

    获取所有可用的实体类型
    """
    try:
        extractor = get_ner_extractor()
        types = extractor.get_entity_types()

        return {"types": types}

    except Exception as e:
        logger.error(f"获取实体类型失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取实体类型失败: {str(e)}")


@router.get("/relation/types")
async def get_relation_types():
    """获取关系类型接口

    获取所有可用的关系类型
    """
    try:
        extractor = get_relation_extractor()
        types = extractor.get_relation_types()

        return {"types": types}

    except Exception as e:
        logger.error(f"获取关系类型失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取关系类型失败: {str(e)}")
