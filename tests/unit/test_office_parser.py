"""Office 文档解析器单元测试"""

import pytest
from unittest.mock import patch, MagicMock
from backend.data_loader.office_parser import WordParser


class TestWordParser:
    """WordParser 测试"""

    def test_parser_creation(self):
        parser = WordParser()
        assert parser is not None
        assert parser._docx_module is None

    def test_init_engine_mock(self):
        """测试延迟加载引擎"""
        parser = WordParser()
        with patch("backend.data_loader.office_parser.HAS_DOCX", True):
            with patch("backend.data_loader.office_parser.Document"):
                result = parser._init_engine()
                assert result is True

    def test_init_engine_no_module(self):
        """测试无 docx 模块时"""
        parser = WordParser()
        with patch("backend.data_loader.office_parser.HAS_DOCX", False):
            result = parser._init_engine()
            assert result is False

    def test_extract_text_no_engine(self):
        """测试无引擎时提取文本"""
        parser = WordParser()
        with patch.object(parser, "_init_engine", return_value=False):
            result = parser.extract_text("/fake/path.docx")
            assert result == ""

    def test_extract_tables_no_engine(self):
        """测试无引擎时提取表格"""
        parser = WordParser()
        with patch.object(parser, "_init_engine", return_value=False):
            result = parser.extract_tables("/fake/path.docx")
            assert result == []
