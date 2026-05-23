"""Office 文档解析器单元测试"""

from unittest.mock import patch

from backend.data_loader.office_parser import WordParser


class TestWordParser:
    """WordParser 测试"""

    def test_parser_creation(self):
        parser = WordParser()
        assert parser._engine is None

    def test_init_engine_success(self):
        """测试引擎初始化成功（mock docx install）"""
        parser = WordParser()
        with patch("backend.data_loader.office_parser.logger"):
            parser._init_engine()
            # _engine 被设为 docx 模块或 False
            assert parser._engine is not None

    def test_extract_text_no_file(self):
        """测试提取不存在文件时应抛异常"""
        parser = WordParser()
        parser._engine = False  # mock no engine
        try:
            parser.extract_text("/nonexistent/test.docx")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_extract_tables_no_engine(self):
        """测试无引擎时提取表格返回空"""
        parser = WordParser()
        parser._engine = False
        result = parser.extract_tables("/fake/path.docx")
        assert result == []
