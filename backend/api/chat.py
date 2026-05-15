"""聊天 API 路由"""
import json
from typing import List, Optional, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.chain import get_rag_chain
from backend.retrieval import get_vector_store
from backend.memory import ConversationMemory

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    """消息模型"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    use_rag: bool = True
    top_k: int = 3


class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str
    session_id: str
    references: List[dict] = []
    sources: List[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """聊天接口 - 调用 RAG 链处理"""
    
    session_id = request.session_id or str(uuid4())
    
    try:
        # 调用 RAG 链
        rag_chain = get_rag_chain()
        result = rag_chain.run(
            query=request.message,
            top_k=request.top_k,
            use_rag=request.use_rag
        )
        
        # 提取来源信息
        sources = []
        for ref in result['references']:
            if ref.get('metadata') and ref['metadata'].get('source'):
                sources.append(ref['metadata']['source'])
        
        return ChatResponse(
            answer=result['answer'],
            session_id=session_id,
            references=result['references'],
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 链调用失败: {str(e)}")


async def generate_stream_response(
    session_id: str,
    message: str,
    use_rag: bool = True,
    top_k: int = 3
) -> AsyncGenerator[str, None]:
    """生成流式响应"""
    try:
        # 获取 RAG 链
        rag_chain = get_rag_chain()
        
        # 保存用户消息到记忆
        memory = ConversationMemory(session_id)
        await memory.save_message("user", message)
        
        # 先发送引用信息（使用正确的 SSE JSON 格式）
        references = rag_chain.get_references(message, top_k=top_k)
        if references:
            ref_json = json.dumps({
                "type": "references",
                "data": references
            }, ensure_ascii=False)
            yield f"data: {ref_json}\n\n"
        
        # 流式生成回答（每个 chunk 直接发送）
        full_answer = ""
        async for chunk in rag_chain.stream_run(message, top_k=top_k, use_rag=use_rag):
            full_answer += chunk
            yield f"data: {chunk}\n\n"
        
        # 保存助手回复到记忆
        await memory.save_message("assistant", full_answer)
        
        # 发送完成信号
        yield f"data: [DONE]\n\n"
        
    except Exception as e:
        error_info = f'[错误: {str(e)}]'
        yield f"data: {error_info}\n\n"
        yield f"data: [DONE]\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口 - SSE"""
    
    session_id = request.session_id or str(uuid4())
    
    return StreamingResponse(
        generate_stream_response(
            session_id=session_id,
            message=request.message,
            use_rag=request.use_rag,
            top_k=request.top_k
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id
        }
    )


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "苏轼文化数字人问答系统"}


@router.post("/docs")
async def add_documents(documents: List[str]):
    """添加文档到向量库"""
    vector_store = get_vector_store()
    ids = vector_store.add_documents(documents)
    return {"status": "success", "added_count": len(ids), "ids": ids}


@router.get("/docs/count")
async def get_document_count():
    """获取向量库文档数量"""
    vector_store = get_vector_store()
    count = vector_store.count()
    return {"count": count}


@router.delete("/docs")
async def clear_documents():
    """清空向量库"""
    vector_store = get_vector_store()
    vector_store.delete_all()
    return {"status": "success", "message": "所有文档已删除"}
