"""状态可视化模块 - 提供中间状态序列化、执行轨迹记录和状态差异比较功能"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class StateSnapshot:
    """状态快照 - 记录执行过程中的某一时刻状态"""

    def __init__(
        self,
        step: int,
        variables: Dict[str, Any],
        call_stack: list,
        timestamp: Optional[datetime] = None,
    ):
        self.step = step
        self.variables = variables
        self.call_stack = call_stack
        self.timestamp = timestamp or datetime.now()
        self.snapshot_id = str(uuid.uuid4())

    def serialize(self) -> Dict[str, Any]:
        """序列化状态快照"""
        return {
            "snapshot_id": self.snapshot_id,
            "step": self.step,
            "timestamp": self.timestamp.isoformat(),
            "variables": self._serialize_variables(self.variables),
            "call_stack": self.call_stack,
        }

    @staticmethod
    def _serialize_variables(variables: Dict[str, Any]) -> Dict[str, Any]:
        """序列化变量字典"""
        result = {}
        for key, value in variables.items():
            try:
                result[key] = json.loads(json.dumps(value, default=str))
            except Exception:
                result[key] = str(value)
        return result

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "StateSnapshot":
        """反序列化状态快照"""
        return cls(
            step=data["step"],
            variables=data["variables"],
            call_stack=data.get("call_stack", []),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class ExecutionTrace:
    """执行轨迹 - 记录整个执行过程的状态变化"""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.snapshots: List[StateSnapshot] = []
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.completed = False

    def add_snapshot(self, snapshot: StateSnapshot):
        """添加状态快照"""
        self.snapshots.append(snapshot)
        logger.debug(f"Added snapshot {snapshot.snapshot_id} for execution {self.execution_id}")

    def get_snapshot(self, step: int) -> Optional[StateSnapshot]:
        """获取指定步骤的快照"""
        for snapshot in self.snapshots:
            if snapshot.step == step:
                return snapshot
        return None

    def get_latest_snapshot(self) -> Optional[StateSnapshot]:
        """获取最新的快照"""
        return self.snapshots[-1] if self.snapshots else None

    def mark_completed(self):
        """标记执行为已完成"""
        self.completed = True
        self.end_time = datetime.now()
        logger.debug(f"Execution {self.execution_id} marked as completed")

    def get_execution_time(self) -> float:
        """获取执行耗时（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def serialize(self) -> Dict[str, Any]:
        """序列化执行轨迹"""
        return {
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "completed": self.completed,
            "execution_time": self.get_execution_time(),
            "snapshots": [s.serialize() for s in self.snapshots],
            "snapshot_count": len(self.snapshots),
        }


class StateVisualizer:
    """状态可视化器 - 管理执行轨迹和状态差异比较"""

    def __init__(self):
        self.traces: Dict[str, ExecutionTrace] = {}
        self.max_snapshots = 1000
        self.max_trace_age_hours = 24

    def create_trace(self, execution_id: str) -> ExecutionTrace:
        """创建新的执行轨迹"""
        trace = ExecutionTrace(execution_id)
        self.traces[execution_id] = trace
        logger.debug(f"Created execution trace: {execution_id}")
        return trace

    def get_trace(self, execution_id: str) -> Optional[ExecutionTrace]:
        """获取执行轨迹"""
        return self.traces.get(execution_id)

    def remove_trace(self, execution_id: str):
        """移除执行轨迹"""
        trace = self.traces.pop(execution_id, None)
        if trace:
            logger.debug(f"Removed execution trace: {execution_id}")

    def record_snapshot(self, execution_id: str, step: int, variables: Dict[str, Any], call_stack: list):
        """记录状态快照"""
        trace = self.traces.get(execution_id)
        if not trace:
            trace = self.create_trace(execution_id)

        if len(trace.snapshots) >= self.max_snapshots:
            trace.snapshots.pop(0)

        snapshot = StateSnapshot(step, variables, call_stack)
        trace.add_snapshot(snapshot)

    def compare_snapshots(
        self, execution_id: str, step1: int, step2: int
    ) -> Dict[str, Any]:
        """比较两个快照之间的差异"""
        trace = self.traces.get(execution_id)
        if not trace:
            return {"error": "Execution trace not found"}

        snap1 = trace.get_snapshot(step1)
        snap2 = trace.get_snapshot(step2)

        if not snap1 or not snap2:
            return {"error": "One or both snapshots not found"}

        diff = {
            "step1": step1,
            "step2": step2,
            "time_diff": (snap2.timestamp - snap1.timestamp).total_seconds(),
            "added_variables": [],
            "removed_variables": [],
            "changed_variables": [],
            "unchanged_variables": [],
        }

        vars1 = snap1.variables
        vars2 = snap2.variables

        for key in vars2:
            if key not in vars1:
                diff["added_variables"].append(key)
            elif vars1[key] != vars2[key]:
                diff["changed_variables"].append({
                    "name": key,
                    "old_value": vars1[key],
                    "new_value": vars2[key],
                })
            else:
                diff["unchanged_variables"].append(key)

        for key in vars1:
            if key not in vars2:
                diff["removed_variables"].append(key)

        return diff

    def get_state_summary(self, execution_id: str) -> Dict[str, Any]:
        """获取执行状态摘要"""
        trace = self.traces.get(execution_id)
        if not trace:
            return {"error": "Execution trace not found"}

        latest_snapshot = trace.get_latest_snapshot()
        summary = {
            "execution_id": execution_id,
            "completed": trace.completed,
            "start_time": trace.start_time.isoformat(),
            "execution_time": trace.get_execution_time(),
            "snapshot_count": len(trace.snapshots),
            "current_step": latest_snapshot.step if latest_snapshot else 0,
        }

        if latest_snapshot:
            summary["variables"] = latest_snapshot.variables
            summary["call_stack"] = latest_snapshot.call_stack

        return summary

    def cleanup_old_traces(self):
        """清理过期的执行轨迹"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_trace_age_hours)
        old_ids = [
            eid for eid, trace in self.traces.items()
            if trace.start_time < cutoff_time
        ]
        for eid in old_ids:
            self.remove_trace(eid)
            logger.debug(f"Cleaned up old trace: {eid}")

    def get_all_traces(self) -> List[Dict[str, Any]]:
        """获取所有执行轨迹的摘要"""
        return [
            {
                "execution_id": eid,
                "completed": trace.completed,
                "start_time": trace.start_time.isoformat(),
                "snapshot_count": len(trace.snapshots),
            }
            for eid, trace in self.traces.items()
        ]


state_visualizer = StateVisualizer()
