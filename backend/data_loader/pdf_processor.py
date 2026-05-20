"""
PDF 处理模块
支持 PDF OCR、表格提取、图表解析等功能
"""

import io
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

try:
    import pytesseract
    from PIL import Image
    import pdfplumber
    import camelot
    import fitz  # PyMuPDF
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TableData:
    """表格数据结构"""
    page_num: int
    table_index: int
    data: List[List[str]]
    bbox: Optional[tuple] = None
    confidence: float = 1.0


@dataclass
class TextBlock:
    """文本块数据结构"""
    page_num: int
    text: str
    bbox: tuple
    font_size: float = 0.0
    font_name: str = ""


@dataclass
class PDFContent:
    """PDF 内容结构"""
    text: str
    tables: List[TableData]
    images: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class PDFProcessor:
    """PDF 处理器"""

    def __init__(self):
        self._tesseract_config = r'--oem 3 --psm 6'

    async def extract_text(self, file_path: str) -> str:
        """提取 PDF 文本内容"""
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text.strip()
        except Exception as e:
            logger.error(f"提取 PDF 文本失败: {str(e)}")
            return ""

    async def extract_tables(self, file_path: str, pages: str = "all") -> List[TableData]:
        """提取 PDF 表格数据"""
        tables = []
        
        try:
            # 使用 camelot 提取表格
            camelot_tables = camelot.read_pdf(file_path, pages=pages, flavor='lattice')
            
            for i, table in enumerate(camelot_tables):
                tables.append(TableData(
                    page_num=table.page,
                    table_index=i,
                    data=table.data,
                    bbox=table.bbox,
                    confidence=table.accuracy / 100
                ))
        except Exception as e:
            logger.warning(f"Camelot 提取表格失败，尝试使用 pdfplumber: {str(e)}")
            
            # 备用方案：使用 pdfplumber
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        page_tables = page.extract_tables()
                        for table_index, table in enumerate(page_tables):
                            if table:
                                tables.append(TableData(
                                    page_num=page_num,
                                    table_index=table_index,
                                    data=table,
                                    confidence=0.8
                                ))
            except Exception as e2:
                logger.error(f"pdfplumber 提取表格失败: {str(e2)}")
        
        return tables

    async def ocr_image(self, image: Image.Image) -> str:
        """对单张图片进行 OCR"""
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract 不可用，无法进行 OCR")
            return ""

        try:
            text = pytesseract.image_to_string(image, config=self._tesseract_config, lang='chi_sim+eng')
            return text.strip()
        except Exception as e:
            logger.error(f"OCR 识别失败: {str(e)}")
            return ""

    async def ocr_pdf(self, file_path: str) -> str:
        """对扫描件 PDF 进行 OCR"""
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract 不可用，无法进行 OCR")
            return ""

        try:
            doc = fitz.open(file_path)
            full_text = ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                
                # 转换为 PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # OCR 识别
                text = await self.ocr_image(image)
                full_text += text + "\n\n"

            return full_text.strip()
        except Exception as e:
            logger.error(f"OCR PDF 失败: {str(e)}")
            return ""

    async def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取 PDF 中的图片"""
        images = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    if base_image:
                        images.append({
                            "page_num": page_num + 1,
                            "index": img_index,
                            "width": base_image["width"],
                            "height": base_image["height"],
                            "format": base_image["ext"],
                            "size": len(base_image["image"])
                        })
        except Exception as e:
            logger.error(f"提取图片失败: {str(e)}")
        
        return images

    async def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """获取 PDF 元数据"""
        metadata = {}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                info = pdf.metadata or {}
                metadata = {
                    "title": info.get("Title", ""),
                    "author": info.get("Author", ""),
                    "subject": info.get("Subject", ""),
                    "keywords": info.get("Keywords", ""),
                    "creator": info.get("Creator", ""),
                    "producer": info.get("Producer", ""),
                    "creation_date": info.get("CreationDate", ""),
                    "mod_date": info.get("ModDate", ""),
                    "page_count": len(pdf.pages)
                }
        except Exception as e:
            logger.error(f"获取元数据失败: {str(e)}")
        
        return metadata

    async def process_pdf(self, file_path: str, enable_ocr: bool = False) -> PDFContent:
        """完整处理 PDF 文件"""
        tasks = [
            self.get_metadata(file_path),
            self.extract_tables(file_path),
            self.extract_images(file_path)
        ]
        
        if enable_ocr:
            tasks.append(self.ocr_pdf(file_path))
            text_task = tasks[-1]
        else:
            tasks.append(self.extract_text(file_path))
            text_task = tasks[-1]
        
        results = await asyncio.gather(*tasks)
        
        return PDFContent(
            text=results[-1],
            tables=results[1],
            images=results[2],
            metadata=results[0]
        )

    async def analyze_layout(self, file_path: str) -> List[TextBlock]:
        """分析 PDF 布局结构"""
        blocks = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_blocks = page.get_text("dict")["blocks"]
                
                for block in text_blocks:
                    if block["type"] == 0:  # 文本块
                        for line in block["lines"]:
                            for span in line["spans"]:
                                blocks.append(TextBlock(
                                    page_num=page_num + 1,
                                    text=span["text"],
                                    bbox=tuple(block["bbox"]),
                                    font_size=span["size"],
                                    font_name=span["font"]
                                ))
        except Exception as e:
            logger.error(f"分析布局失败: {str(e)}")
        
        return blocks

    def tables_to_markdown(self, tables: List[TableData]) -> str:
        """将表格数据转换为 Markdown 格式"""
        markdown = ""
        
        for table in tables:
            markdown += f"## 表格 {table.table_index + 1} (第 {table.page_num} 页)\n\n"
            
            if table.data:
                # 表头
                markdown += "| " + " | ".join(table.data[0]) + " |\n"
                markdown += "| " + " | ".join(["---"] * len(table.data[0])) + " |\n"
                
                # 数据行
                for row in table.data[1:]:
                    markdown += "| " + " | ".join(str(cell) for cell in row) + " |\n"
            
            markdown += "\n"
        
        return markdown.strip()


# 全局 PDF 处理器实例
pdf_processor = PDFProcessor()


async def process_pdf_file(file_path: str, enable_ocr: bool = False) -> Dict[str, Any]:
    """处理 PDF 文件并返回结构化结果"""
    content = await pdf_processor.process_pdf(file_path, enable_ocr)
    
    return {
        "text": content.text,
        "tables": [
            {
                "page_num": t.page_num,
                "table_index": t.table_index,
                "data": t.data,
                "confidence": t.confidence
            } for t in content.tables
        ],
        "images": content.images,
        "metadata": content.metadata,
        "tables_markdown": pdf_processor.tables_to_markdown(content.tables)
    }


async def extract_pdf_tables(file_path: str) -> List[Dict[str, Any]]:
    """提取 PDF 表格"""
    tables = await pdf_processor.extract_tables(file_path)
    return [
        {
            "page_num": t.page_num,
            "table_index": t.table_index,
            "data": t.data,
            "confidence": t.confidence
        } for t in tables
    ]


async def ocr_scanned_pdf(file_path: str) -> str:
    """对扫描件 PDF 进行 OCR"""
    return await pdf_processor.ocr_pdf(file_path)