"""文件上传模块"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileInfo:
    """文件信息"""

    file_id: str
    filename: str
    size: int
    content_type: str
    upload_time: datetime
    path: str

    def to_dict(self):
        """转换为字典"""
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "upload_time": self.upload_time.isoformat(),
            "path": self.path,
        }


class FileUploadService:
    """文件上传服务"""

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR = Path("uploads")

    def __init__(self):
        self._files = {}
        self.UPLOAD_DIR.mkdir(exist_ok=True)

    def validate_file(self, filename: str, size: int, content_type: str) -> tuple[bool, Optional[str]]:
        """验证文件

        Args:
            filename: 文件名
            size: 文件大小
            content_type: 文件类型

        Returns:
            (是否有效, 错误信息)
        """
        if not filename:
            return False, "文件名不能为空"

        if size > self.MAX_FILE_SIZE:
            max_size_mb = self.MAX_FILE_SIZE // (1024 * 1024)
            return False, f"文件大小超过限制（最大{max_size_mb}MB）"

        allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf", "text/plain", "application/json"]

        if content_type not in allowed_types:
            return False, f"不支持的文件类型：{content_type}"

        return True, None

    def save_file(
        self, filename: str, content: bytes, content_type: str
    ) -> tuple[bool, Optional[FileInfo], Optional[str]]:
        """保存文件

        Args:
            filename: 文件名
            content: 文件内容
            content_type: 文件类型

        Returns:
            (是否成功, 文件信息, 错误信息)
        """
        is_valid, error = self.validate_file(filename, len(content), content_type)
        if not is_valid:
            return False, None, error

        file_id = str(uuid.uuid4())
        upload_time = datetime.now()

        extension = Path(filename).suffix
        saved_filename = f"{file_id}{extension}"
        file_path = self.UPLOAD_DIR / saved_filename

        with open(file_path, "wb") as f:
            f.write(content)

        file_info = FileInfo(
            file_id=file_id,
            filename=filename,
            size=len(content),
            content_type=content_type,
            upload_time=upload_time,
            path=str(file_path),
        )

        self._files[file_id] = file_info
        return True, file_info, None

    def get_file(self, file_id: str) -> Optional[FileInfo]:
        """获取文件信息

        Args:
            file_id: 文件ID

        Returns:
            文件信息或None
        """
        return self._files.get(file_id)

    def delete_file(self, file_id: str) -> tuple[bool, Optional[str]]:
        """删除文件

        Args:
            file_id: 文件ID

        Returns:
            (是否成功, 错误信息)
        """
        file_info = self._files.get(file_id)
        if not file_info:
            return False, "文件不存在"

        try:
            file_path = Path(file_info.path)
            if file_path.exists():
                file_path.unlink()

            del self._files[file_id]
            return True, None

        except Exception as e:
            return False, f"删除文件失败：{str(e)}"
