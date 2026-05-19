"""文档分块模块 - 实现多种智能分块策略"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    """文档分块器 - 支持多种分块策略"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        tokenizer: Optional[Any] = None,
    ):
        """
        Args:
            chunk_size: 每个分块的大小（token或字符）
            chunk_overlap: 分块间的重叠
            tokenizer: 可选的tokenizer
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer

        if tokenizer:
            self._count_tokens = lambda x: len(tokenizer.encode(x))
        else:
            self._count_tokens = lambda x: len(x)

    def split_text(self, text: str) -> List[str]:
        """分块文本（默认方法）"""
        return self._semantic_split(text)

    def _simple_split(self, text: str) -> List[str]:
        """简单按字符分块"""
        chunks = []
        i = 0
        while i < len(text):
            end = i + self.chunk_size
            chunk = text[i:end]
            chunks.append(chunk)
            i += self.chunk_size - self.chunk_overlap
        return chunks

    def _semantic_split(self, text: str) -> List[str]:
        """语义感知分块 - 按句子和段落分割"""
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current_chunk = ""
        current_size = 0

        for para in paragraphs:
            sentences = self._split_sentences(para)

            for sent in sentences:
                sent_size = self._count_tokens(sent)

                if current_size + sent_size > self.chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = self._get_overlap(current_chunk)
                    current_size = self._count_tokens(current_chunk)

                current_chunk += sent + " "
                current_size += sent_size

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        logger.debug(f"语义分块完成: {len(text)} chars -> {len(chunks)} chunks")
        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割"""
        paragraphs = re.split(r"\n\s*\n", text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割（中英文支持）"""
        pattern = r"[。！？.!?]\s*"
        sentences = re.split(pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        result = []
        for s in sentences:
            result.append(s + self._get_ending(text, s))

        return result

    def _get_ending(self, full_text: str, sentence: str) -> str:
        """获取句子结尾符号"""
        idx = full_text.find(sentence)
        if idx == -1 or idx + len(sentence) >= len(full_text):
            return ""
        next_char = full_text[idx + len(sentence)]
        if next_char in "。！？.!?":
            return next_char
        return ""

    def _get_overlap(self, text: str) -> str:
        """获取重叠部分"""
        if self.chunk_overlap <= 0:
            return ""

        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            overlap_tokens = tokens[-self.chunk_overlap:]
            return self.tokenizer.decode(overlap_tokens, skip_special_tokens=True)
        else:
            return text[-self.chunk_overlap:] if len(text) > self.chunk_overlap else text


class MarkdownChunker(DocumentChunker):
    """Markdown专用分块器 - 按标题结构分块"""

    def split_text(self, text: str) -> List[str]:
        """Markdown分块 - 保持标题和内容在一起"""
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = self._count_tokens(line + "\n")

            if line.startswith("#"):
                if current_chunk:
                    chunks.append("\n".join(current_chunk).strip())

                if current_size > self.chunk_size * 0.3:
                    overlap = self._get_overlap("\n".join(current_chunk))
                    current_chunk = [overlap, line]
                    current_size = self._count_tokens(overlap) + line_size
                else:
                    current_chunk = [line]
                    current_size = line_size
            else:
                if current_size + line_size > self.chunk_size and current_chunk:
                    chunks.append("\n".join(current_chunk).strip())
                    overlap = self._get_overlap("\n".join(current_chunk))
                    current_chunk = [overlap, line]
                    current_size = self._count_tokens(overlap) + line_size
                else:
                    current_chunk.append(line)
                    current_size += line_size

        if current_chunk:
            chunks.append("\n".join(current_chunk).strip())

        logger.debug(f"Markdown分块完成: {len(chunks)} chunks")
        return chunks


class RecursiveCharacterChunker(DocumentChunker):
    """递归字符分块 - LangChain风格的递归分割"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        tokenizer: Optional[Any] = None,
        separators: Optional[List[str]] = None,
    ):
        super().__init__(chunk_size, chunk_overlap, tokenizer)

        if separators is None:
            self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        else:
            self.separators = separators

    def split_text(self, text: str) -> List[str]:
        """递归分块"""
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """递归分割"""
        if not separators:
            return self._simple_split(text)

        separator = separators[0]
        if separator:
            chunks = text.split(separator)
        else:
            chunks = list(text)

        good_chunks = []
        bad_chunks = []

        for chunk in chunks:
            if self._count_tokens(chunk) < self.chunk_size:
                good_chunks.append(chunk)
            else:
                bad_chunks.append(chunk)

        merged = self._merge_splits(good_chunks, separator)
        result = []

        for chunk in bad_chunks:
            result.extend(self._split_recursive(chunk, separators[1:]))

        final = self._merge_splits(merged + result, "")
        return final

    def _merge_splits(self, chunks: List[str], separator: str) -> List[str]:
        """合并小分块"""
        merged = []
        current = ""
        current_size = 0

        for chunk in chunks:
            chunk_size = self._count_tokens(chunk)

            if current_size + chunk_size > self.chunk_size:
                if current:
                    merged.append(current)
                overlap = self._get_overlap(current) if current else ""
                current = overlap + separator + chunk if overlap else chunk
                current_size = self._count_tokens(current)
            else:
                if current:
                    current += separator + chunk
                else:
                    current = chunk
                current_size += chunk_size

        if current:
            merged.append(current)

        return merged


def get_chunker(
    file_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
) -> DocumentChunker:
    """获取适当的分块器"""
    ext = Path(file_path).suffix.lower()

    if ext in [".md", ".markdown"]:
        return MarkdownChunker(chunk_size, chunk_overlap)
    else:
        return RecursiveCharacterChunker(chunk_size, chunk_overlap)
