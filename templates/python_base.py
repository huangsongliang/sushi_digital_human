"""模块文档字符串 - 请替换为实际描述"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class BaseClass(Enum):
    """类文档字符串 - 请替换为实际描述"""
    
    OPTION_ONE = "option_one"
    OPTION_TWO = "option_two"


@dataclass
class DataStructure:
    """数据结构文档字符串 - 请替换为实际描述"""
    
    field_one: str
    field_two: int
    field_three: Optional[List[str]] = None


def example_function(param_one: str, param_two: Optional[int] = None) -> Dict[str, Any]:
    """函数文档字符串 - 请替换为实际描述
    
    Args:
        param_one: 参数一的说明
        param_two: 参数二的说明（可选）
    
    Returns:
        返回值的说明
    """
    result = {
        "success": True,
        "data": {
            "param_one": param_one,
            "param_two": param_two
        }
    }
    return result


async def async_example_function() -> str:
    """异步函数文档字符串 - 请替换为实际描述"""
    return "async result"