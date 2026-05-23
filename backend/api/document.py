"""文档处理 API 路由"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.data_loader.chunker import get_chunker
from backend.data_loader.loader import DocumentLoader
from backend.data_loader.pdf_processor import process_pdf_file
from backend.retrieval import get_vector_store
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/docs", tags=["文档处理"])


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    status: str
    file_name: str
    document_id: str
    chunks: int
    message: str


class DocumentProcessRequest(BaseModel):
    """文档处理请求"""

    use_ocr: bool = True
    extract_tables: bool = True
    extract_images: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 100


class DocumentProcessResponse(BaseModel):
    """文档处理响应"""

    status: str
    file_name: str
    text_length: int
    tables_count: int
    images_count: int
    chunks: List[str]
    metadata: dict


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    use_ocr: bool = True,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
):
    """上传并处理文档"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        file_ext = Path(file.filename).suffix.lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            loader = DocumentLoader()
            documents = []

            if file_ext == ".pdf":
                logger.info(f"处理 PDF 文件: {file.filename}")
                result = process_pdf_file(
                    file_path=tmp_file_path,
                    use_ocr=use_ocr,
                    extract_tables=True,
                    extract_images=False,
                )

                if result.get("tables"):
                    table_texts = [f"表格 {i + 1}:\n{t['content']}" for i, t in enumerate(result["tables"])]
                    documents.append(result["text"])
                    documents.extend(table_texts)
                else:
                    documents.append(result["text"])

            elif file_ext in [".txt", ".md", ".json", ".csv", ".jsonl"]:
                documents = loader.load_from_file(tmp_file_path)

            else:
                raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")

            if not documents:
                raise HTTPException(status_code=400, detail="文档内容为空")

            all_chunks = []
            chunker = get_chunker(file.filename, chunk_size, chunk_overlap)

            for doc in documents:
                if doc.strip():
                    chunks = chunker.split_text(doc)
                    all_chunks.extend(chunks)

            vector_store = get_vector_store()
            chunk_texts = [c for c in all_chunks if c.strip()]
            metadatas = [
                {
                    "source": file.filename,
                    "chunk_index": i,
                    "total_chunks": len(chunk_texts),
                }
                for i in range(len(chunk_texts))
            ]

            doc_ids = vector_store.add_documents(chunk_texts, metadatas=metadatas)

            logger.info(f"文档上传成功: {file.filename}, {len(doc_ids)} 个块")

            return DocumentUploadResponse(
                status="success",
                file_name=file.filename,
                document_id=doc_ids[0] if doc_ids else "",
                chunks=len(doc_ids),
                message="文档处理成功",
            )

        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.post("/process", response_model=DocumentProcessResponse)
async def process_document(
    file: UploadFile = File(...),
    use_ocr: bool = True,
    extract_tables: bool = True,
    extract_images: bool = False,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
):
    """处理文档（返回处理结果，不上传到向量库）"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        file_ext = Path(file.filename).suffix.lower()

        if file_ext != ".pdf":
            raise HTTPException(status_code=400, detail="目前仅支持 PDF 文件的处理")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            result = process_pdf_file(
                file_path=tmp_file_path,
                use_ocr=use_ocr,
                extract_tables=extract_tables,
                extract_images=extract_images,
            )

            chunker = get_chunker(file.filename, chunk_size, chunk_overlap)
            chunks = chunker.split_text(result["text"])
            chunks = [c for c in chunks if c.strip()]

            return DocumentProcessResponse(
                status="success",
                file_name=file.filename,
                text_length=len(result["text"]),
                tables_count=len(result.get("tables", [])),
                images_count=len(result.get("images", [])),
                chunks=chunks,
                metadata=result.get("metadata", {}),
            )

        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.post("/batch/upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    use_ocr: bool = True,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
):
    """批量上传文档"""
    results = []
    errors = []

    for file in files:
        try:
            if not file.filename:
                errors.append({"file": "unknown", "error": "文件名为空"})
                continue

            file_ext = Path(file.filename).suffix.lower()

            if file_ext not in [".pdf", ".txt", ".md", ".json", ".csv"]:
                errors.append({"file": file.filename, "error": f"不支持的格式: {file_ext}"})
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            try:
                loader = DocumentLoader()
                documents = []

                if file_ext == ".pdf":
                    result = process_pdf_file(
                        file_path=tmp_file_path,
                        use_ocr=use_ocr,
                        extract_tables=True,
                        extract_images=False,
                    )
                    documents.append(result["text"])
                else:
                    documents = loader.load_from_file(tmp_file_path)

                if documents:
                    chunker = get_chunker(file.filename, chunk_size, chunk_overlap)
                    all_chunks = []
                    for doc in documents:
                        if doc.strip():
                            chunks = chunker.split_text(doc)
                            all_chunks.extend(chunks)

                    vector_store = get_vector_store()
                    chunk_texts = [c for c in all_chunks if c.strip()]
                    metadatas = [
                        {
                            "source": file.filename,
                            "chunk_index": i,
                            "total_chunks": len(chunk_texts),
                        }
                        for i in range(len(chunk_texts))
                    ]

                    doc_ids = vector_store.add_documents(chunk_texts, metadatas=metadatas)

                    results.append(
                        {
                            "file": file.filename,
                            "status": "success",
                            "chunks": len(doc_ids),
                        }
                    )

            finally:
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return {
        "status": "completed",
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


@router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的文档格式"""
    return {
        "formats": [
            {"extension": ".pdf", "name": "PDF 文档", "ocr": True, "table_extraction": True},
            {"extension": ".txt", "name": "文本文件", "ocr": False, "table_extraction": False},
            {"extension": ".md", "name": "Markdown", "ocr": False, "table_extraction": False},
            {"extension": ".json", "name": "JSON", "ocr": False, "table_extraction": False},
            {"extension": ".csv", "name": "CSV 表格", "ocr": False, "table_extraction": True},
        ]
    }
