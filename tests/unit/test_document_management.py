"""文档管理模块单元测试"""

import pytest
import tempfile
import json
from pathlib import Path
from backend.data_loader.chunker import (
    DocumentChunker,
    MarkdownChunker,
    RecursiveCharacterChunker,
    get_chunker,
)


class TestDocumentChunker:
    """文档分块器测试"""

    def test_simple_split(self):
        chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)
        text = "1234567890abcdefghij"

        chunks = chunker._simple_split(text)

        assert len(chunks) > 0

    def test_semantic_split(self):
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        text = "这是第一段。这是第二段。这是第三段。这是第四段。这是第五段。"

        chunks = chunker._semantic_split(text)

        assert len(chunks) > 0
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_split_paragraphs(self):
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        text = "第一段\n\n第二段\n\n第三段"

        paragraphs = chunker._split_paragraphs(text)

        assert len(paragraphs) == 3
        assert paragraphs[0] == "第一段"
        assert paragraphs[1] == "第二段"
        assert paragraphs[2] == "第三段"

    def test_split_sentences(self):
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        text = "第一句。第二句！第三句？"

        sentences = chunker._split_sentences(text)

        assert len(sentences) >= 1


class TestMarkdownChunker:
    """Markdown 分块器测试"""

    def test_markdown_split_with_headers(self):
        chunker = MarkdownChunker(chunk_size=100, chunk_overlap=20)
        markdown_text = (
            "# 标题1\n\n"
            "这是标题1的内容。\n\n"
            "## 标题2\n\n"
            "这是标题2的内容。"
        )

        chunks = chunker.split_text(markdown_text)

        assert len(chunks) > 0


class TestRecursiveCharacterChunker:
    """递归字符分块器测试"""

    def test_recursive_split_simple(self):
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
        text = "这是第一段。这是第二段。这是第三段。这是第四段。"

        chunks = chunker.split_text(text)

        assert len(chunks) > 0


class TestGetChunker:
    """获取分块器测试"""

    def test_get_markdown_chunker(self):
        chunker = get_chunker("test.md", chunk_size=100, chunk_overlap=20)
        assert isinstance(chunker, MarkdownChunker)

    def test_get_recursive_chunker(self):
        chunker = get_chunker("test.txt", chunk_size=100, chunk_overlap=20)
        assert isinstance(chunker, RecursiveCharacterChunker)

    def test_get_recursive_chunker_other_ext(self):
        chunker = get_chunker("test.json", chunk_size=100, chunk_overlap=20)
        assert isinstance(chunker, RecursiveCharacterChunker)
