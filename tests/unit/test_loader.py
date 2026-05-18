"""数据加载器单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from backend.data_loader.loader import DocumentLoader


class TestDocumentLoader:
    """文档加载器测试"""

    def test_loader_creation(self):
        with patch('backend.data_loader.loader.get_vector_store'):
            loader = DocumentLoader()
            assert loader is not None

    def test_load_txt_file(self):
        with patch('backend.data_loader.loader.get_vector_store'):
            loader = DocumentLoader()
            with patch('builtins.open', MagicMock(
                read=MagicMock(return_value="test content")
            )):
                with patch('backend.data_loader.loader.Path') as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.suffix.lower.return_value = ".txt"
                    mock_path.return_value.__fspath__.return_value = "test.txt"
                    content = loader.load_from_file("test.txt")
                    assert content is not None
                    assert isinstance(content, list)

    def test_load_markdown_file(self):
        with patch('backend.data_loader.loader.get_vector_store'):
            loader = DocumentLoader()
            with patch('builtins.open', MagicMock(
                read=MagicMock(return_value="# Title\nContent")
            )):
                with patch('backend.data_loader.loader.Path') as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.suffix.lower.return_value = ".md"
                    mock_path.return_value.__fspath__.return_value = "test.md"
                    content = loader.load_from_file("test.md")
                    assert content is not None

    def test_load_nonexistent_file(self):
        with patch('backend.data_loader.loader.get_vector_store'):
            loader = DocumentLoader()
            with patch('backend.data_loader.loader.Path') as mock_path:
                mock_path.return_value.exists.return_value = False
                with pytest.raises(FileNotFoundError):
                    loader.load_from_file("nonexistent.txt")

    def test_load_unsupported_file(self):
        with patch('backend.data_loader.loader.get_vector_store'):
            loader = DocumentLoader()
            with patch('backend.data_loader.loader.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.suffix.lower.return_value = ".exe"
                with pytest.raises(ValueError):
                    loader.load_from_file("test.exe")
