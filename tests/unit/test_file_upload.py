"""文件上传模块单元测试"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from backend.utils.file_upload import FileUploadService, FileInfo


class TestFileUploadService:
    """文件上传服务测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = FileUploadService()

    def teardown_method(self):
        """测试后清理"""
        if self.service.UPLOAD_DIR.exists():
            shutil.rmtree(self.service.UPLOAD_DIR)

    def test_validate_file_valid(self):
        """测试有效文件验证"""
        is_valid, error = self.service.validate_file(
            "test.jpg", 1024, "image/jpeg"
        )
        assert is_valid is True
        assert error is None

    def test_validate_file_empty_name(self):
        """测试空文件名"""
        is_valid, error = self.service.validate_file(
            "", 1024, "image/jpeg"
        )
        assert is_valid is False
        assert "不能为空" in error

    def test_validate_file_too_large(self):
        """测试文件过大"""
        is_valid, error = self.service.validate_file(
            "test.jpg", 200 * 1024 * 1024, "image/jpeg"
        )
        assert is_valid is False
        assert "超过限制" in error

    def test_validate_file_invalid_type(self):
        """测试无效文件类型"""
        is_valid, error = self.service.validate_file(
            "test.exe", 1024, "application/octet-stream"
        )
        assert is_valid is False
        assert "不支持" in error

    def test_save_file(self):
        """测试保存文件"""
        content = b"test file content"
        success, file_info, error = self.service.save_file(
            "test.txt", content, "text/plain"
        )

        assert success is True
        assert error is None
        assert file_info is not None
        assert file_info.filename == "test.txt"
        assert file_info.size == len(content)
        assert file_info.content_type == "text/plain"

    def test_get_file(self):
        """测试获取文件信息"""
        content = b"test content"
        success, file_info, _ = self.service.save_file(
            "test.txt", content, "text/plain"
        )

        retrieved = self.service.get_file(file_info.file_id)
        assert retrieved is not None
        assert retrieved.filename == "test.txt"

    def test_get_file_not_found(self):
        """测试获取不存在的文件"""
        result = self.service.get_file("nonexistent-id")
        assert result is None

    def test_delete_file(self):
        """测试删除文件"""
        content = b"test content"
        success, file_info, _ = self.service.save_file(
            "test.txt", content, "text/plain"
        )

        delete_success, delete_error = self.service.delete_file(file_info.file_id)
        assert delete_success is True
        assert delete_error is None

        retrieved = self.service.get_file(file_info.file_id)
        assert retrieved is None

    def test_delete_file_not_found(self):
        """测试删除不存在的文件"""
        success, error = self.service.delete_file("nonexistent-id")
        assert success is False
        assert "不存在" in error


class TestFileInfo:
    """文件信息测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        file_info = FileInfo(
            file_id="test-id",
            filename="test.txt",
            size=1024,
            content_type="text/plain",
            upload_time=datetime(2024, 1, 1, 12, 0, 0),
            path="/path/to/file"
        )

        result = file_info.to_dict()
        assert result["file_id"] == "test-id"
        assert result["filename"] == "test.txt"
        assert result["size"] == 1024
        assert result["content_type"] == "text/plain"
        assert "2024-01-01" in result["upload_time"]
