"""PDF 文档处理模块
支持 PDF 文本提取、OCR 识别、表格提取
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """PDF 文档处理器"""

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_lang: str = "ch+eng",
        table_detection: bool = True,
    ):
        """
        Args:
            use_ocr: 是否使用 OCR 识别扫描件
            ocr_lang: OCR 语言设置
            table_detection: 是否启用表格检测
        """
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        self.table_detection = table_detection
        self._ocr_engine = None
        self._pdf_engine = None

    def _init_ocr_engine(self):
        """延迟初始化 OCR 引擎"""
        if self._ocr_engine is None:
            try:
                import easyocr

                self._ocr_engine = easyocr.Reader([self.ocr_lang], gpu=False, verbose=False)
                logger.info("OCR 引擎初始化成功")
            except ImportError:
                logger.warning("EasyOCR 未安装，OCR 功能将不可用")
                self._ocr_engine = False

    def _init_pdf_engine(self):
        """延迟初始化 PDF 处理引擎"""
        if self._pdf_engine is None:
            try:
                import fitz

                self._pdf_engine = fitz
                logger.info("PDF 引擎 (PyMuPDF) 初始化成功")
            except ImportError:
                logger.warning("PyMuPDF 未安装，PDF 处理功能将受限")
                self._pdf_engine = False

    def extract_text(self, file_path: str) -> str:
        """提取 PDF 文本内容"""
        self._init_pdf_engine()

        if not self._pdf_engine:
            raise RuntimeError("PDF 处理引擎未初始化，请安装 PyMuPDF: pip install pymupdf")

        try:
            doc = self._pdf_engine.open(file_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                if not text.strip() and self.use_ocr:
                    logger.info(f"页面 {page_num + 1} 无文本，使用 OCR 识别")
                    text = self._ocr_page(page)

                text_parts.append(text)

            doc.close()
            full_text = "\n\n".join(text_parts)
            logger.info(f"PDF 文本提取完成: {len(full_text)} 字符")
            return full_text

        except Exception as e:
            logger.error(f"PDF 文本提取失败: {str(e)}")
            raise

    def _ocr_page(self, page) -> str:
        """对单个 PDF 页面进行 OCR 识别"""
        self._init_ocr_engine()

        if not self._ocr_engine:
            logger.warning("OCR 引擎不可用")
            return ""

        try:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            results = self._ocr_engine.readtext(img_bytes)
            text_parts = [result[1] for result in results]

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"OCR 识别失败: {str(e)}")
            return ""

    def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """提取 PDF 中的表格"""
        self._init_pdf_engine()

        if not self._pdf_engine:
            return []

        try:
            doc = self._pdf_engine.open(file_path)
            tables = []

            for page_num in range(len(doc)):
                page = doc[page_num]

                text = page.get_text()
                table_blocks = self._detect_table_blocks(text)

                for block in table_blocks:
                    tables.append(
                        {
                            "page": page_num + 1,
                            "content": block["content"],
                            "rows": block.get("rows", 0),
                            "cols": block.get("cols", 0),
                            "bbox": block.get("bbox"),
                        }
                    )

            doc.close()
            logger.info(f"PDF 表格提取完成: {len(tables)} 个表格")
            return tables

        except Exception as e:
            logger.error(f"PDF 表格提取失败: {str(e)}")
            return []

    def _detect_table_blocks(self, text: str) -> List[Dict[str, Any]]:
        """检测文本中的表格结构"""
        lines = text.split("\n")
        tables = []

        current_table: list[str] = []
        in_table = False

        for line in lines:
            if self._is_table_line(line):
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append(
                        {
                            "content": "\n".join(current_table),
                            "rows": len(current_table),
                            "cols": self._count_columns(current_table),
                        }
                    )
                    current_table = []
                    in_table = False

        if current_table:
            tables.append(
                {
                    "content": "\n".join(current_table),
                    "rows": len(current_table),
                    "cols": self._count_columns(current_table),
                }
            )

        return tables

    def _is_table_line(self, line: str) -> bool:
        """判断是否为表格行"""
        separators = ["|", "│", "┌", "┐", "└", "┘", "├", "┤", "─", "┼"]
        has_separator = any(sep in line for sep in separators)
        has_multiple_tabs = line.count("\t") >= 2

        return has_separator or has_multiple_tabs

    def _count_columns(self, lines: List[str]) -> int:
        """计算表格列数"""
        if not lines:
            return 0

        max_cols = 0
        for line in lines:
            cols = len([c for c in line.split("|") if c.strip()])
            max_cols = max(max_cols, cols)

        return max_cols

    def extract_images(self, file_path: str, output_dir: Optional[str] = None) -> List[str]:
        """提取 PDF 中的图片"""
        self._init_pdf_engine()

        if not self._pdf_engine:
            return []

        try:
            doc = self._pdf_engine.open(file_path)
            image_paths = []

            if output_dir is None:
                output_dir = Path(file_path).parent / f"{Path(file_path).stem}_images"
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    image_name = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    image_path = output_dir / image_name

                    with open(image_path, "wb") as image_file:
                        image_file.write(image_bytes)

                    image_paths.append(str(image_path))

            doc.close()
            logger.info(f"PDF 图片提取完成: {len(image_paths)} 张图片")
            return image_paths

        except Exception as e:
            logger.error(f"PDF 图片提取失败: {str(e)}")
            return []

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取 PDF 元数据"""
        self._init_pdf_engine()

        if not self._pdf_engine:
            return {}

        try:
            doc = self._pdf_engine.open(file_path)
            metadata = doc.metadata

            result = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "pages": len(doc),
                "file_size": Path(file_path).stat().st_size,
            }

            doc.close()
            return result

        except Exception as e:
            logger.error(f"PDF 元数据提取失败: {str(e)}")
            return {}

    def process(self, file_path: str, extract_tables: bool = True, extract_images: bool = False) -> Dict[str, Any]:
        """
        完整处理 PDF 文件

        Args:
            file_path: PDF 文件路径
            extract_tables: 是否提取表格
            extract_images: 是否提取图片

        Returns:
            处理结果字典
        """
        result = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "metadata": self.extract_metadata(file_path),
            "text": self.extract_text(file_path),
            "tables": [],
            "images": [],
        }

        if extract_tables:
            result["tables"] = self.extract_tables(file_path)  # type: ignore[assignment]

        if extract_images:
            result["images"] = self.extract_images(file_path)

        logger.info(f"PDF 处理完成: {file_path}")
        return result


def process_pdf_file(
    file_path: str,
    use_ocr: bool = True,
    extract_tables: bool = True,
    extract_images: bool = False,
) -> Dict[str, Any]:
    """便捷函数：处理 PDF 文件"""
    processor = PDFProcessor(use_ocr=use_ocr, table_detection=extract_tables)
    return processor.process(file_path, extract_tables=extract_tables, extract_images=extract_images)


def extract_pdf_text(file_path: str, use_ocr: bool = True) -> str:
    """便捷函数：提取 PDF 文本"""
    processor = PDFProcessor(use_ocr=use_ocr)
    return processor.extract_text(file_path)
