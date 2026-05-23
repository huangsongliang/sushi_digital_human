"""断点管理模块 - 提供断点设置、获取、删除和命中检测功能"""

import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BreakpointStatus(str, Enum):
    """断点状态枚举"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"


class Breakpoint:
    """断点模型"""

    def __init__(
        self,
        location: str,
        condition: Optional[str] = None,
        enabled: bool = True,
        breakpoint_id: Optional[str] = None,
    ):
        self.id = breakpoint_id or str(uuid.uuid4())
        self.location = location
        self.condition = condition
        self.enabled = enabled
        self.hit_count = 0
        self.last_hit = None

    def is_enabled(self) -> bool:
        """检查断点是否启用"""
        return self.enabled

    def should_break(self, variables: Dict[str, Any]) -> bool:
        """判断是否应该触发断点"""
        if not self.enabled:
            return False

        if self.condition:
            try:
                return eval(self.condition, {}, variables)
            except Exception as e:
                logger.error(f"Failed to evaluate breakpoint condition: {e}")
                return False

        return True

    def hit(self):
        """记录断点命中"""
        self.hit_count += 1
        self.last_hit = True

    def reset_hit_count(self):
        """重置命中计数"""
        self.hit_count = 0
        self.last_hit = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "location": self.location,
            "condition": self.condition,
            "enabled": self.enabled,
            "hit_count": self.hit_count,
            "last_hit": self.last_hit,
        }


class BreakpointManager:
    """断点管理器 - 管理所有断点的生命周期"""

    def __init__(self):
        self.breakpoints: Dict[str, Breakpoint] = {}
        self._location_index: Dict[str, List[str]] = {}

    def add_breakpoint(
        self,
        location: str,
        condition: Optional[str] = None,
        enabled: bool = True,
    ) -> Breakpoint:
        """添加断点"""
        bp = Breakpoint(location, condition, enabled)
        self.breakpoints[bp.id] = bp

        if location not in self._location_index:
            self._location_index[location] = []
        self._location_index[location].append(bp.id)

        logger.debug(f"Added breakpoint: {bp.id} at {location}")
        return bp

    def get_breakpoint(self, breakpoint_id: str) -> Optional[Breakpoint]:
        """获取断点"""
        return self.breakpoints.get(breakpoint_id)

    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """删除断点"""
        bp = self.breakpoints.pop(breakpoint_id, None)
        if bp:
            if bp.location in self._location_index:
                self._location_index[bp.location].remove(breakpoint_id)
                if not self._location_index[bp.location]:
                    del self._location_index[bp.location]
            logger.debug(f"Removed breakpoint: {breakpoint_id}")
            return True
        return False

    def get_all_breakpoints(self) -> List[Breakpoint]:
        """获取所有断点"""
        return list(self.breakpoints.values())

    def get_breakpoints_by_location(self, location: str) -> List[Breakpoint]:
        """按位置获取断点"""
        ids = self._location_index.get(location, [])
        return [self.breakpoints[id_] for id_ in ids if id_ in self.breakpoints]

    def update_breakpoint(
        self,
        breakpoint_id: str,
        condition: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """更新断点属性"""
        bp = self.breakpoints.get(breakpoint_id)
        if not bp:
            return False

        if condition is not None:
            bp.condition = condition
        if enabled is not None:
            bp.enabled = enabled

        logger.debug(f"Updated breakpoint: {breakpoint_id}")
        return True

    def toggle_breakpoint(self, breakpoint_id: str) -> bool:
        """切换断点启用状态"""
        bp = self.breakpoints.get(breakpoint_id)
        if bp:
            bp.enabled = not bp.enabled
            logger.debug(f"Toggled breakpoint {breakpoint_id}: {bp.enabled}")
            return True
        return False

    def check_breakpoints(self, location: str, variables: Dict[str, Any]) -> List[Breakpoint]:
        """检查指定位置是否有断点命中"""
        hit_breakpoints = []
        for bp in self.get_breakpoints_by_location(location):
            if bp.should_break(variables):
                bp.hit()
                hit_breakpoints.append(bp)
                logger.debug(f"Breakpoint hit: {bp.id} at {location}")

        return hit_breakpoints

    def clear_all_breakpoints(self):
        """清除所有断点"""
        self.breakpoints.clear()
        self._location_index.clear()
        logger.debug("Cleared all breakpoints")

    def reset_all_hit_counts(self):
        """重置所有断点的命中计数"""
        for bp in self.breakpoints.values():
            bp.reset_hit_count()


breakpoint_manager = BreakpointManager()
