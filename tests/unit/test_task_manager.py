"""任务管理器模块单元测试"""
from backend.utils.task_manager import (
    Task,
    TaskStatus,
    MemoryTaskStorage,
    TaskManager,
    get_task_manager
)


class TestTask:
    """任务模型测试"""

    def test_task_creation(self):
        task = Task(
            task_id="task123",
            func_name="test_func"
        )
        assert task.task_id == "task123"
        assert task.status == TaskStatus.PENDING

    def test_task_duration(self):
        task = Task(
            task_id="task123",
            func_name="test_func"
        )
        duration = task.duration
        assert duration >= 0

    def test_task_is_complete(self):
        task = Task(
            task_id="task123",
            func_name="test_func",
            status=TaskStatus.COMPLETED
        )
        assert task.is_complete is True

    def test_task_to_dict(self):
        task = Task(
            task_id="task123",
            func_name="test_func"
        )
        result = task.to_dict()
        assert result["task_id"] == "task123"


class TestMemoryTaskStorage:
    """内存任务存储测试"""

    def test_storage_set_and_get(self):
        storage = MemoryTaskStorage()
        task = Task(
            task_id="task123",
            func_name="test_func"
        )
        storage.set(task)
        retrieved = storage.get("task123")
        assert retrieved is not None
        assert retrieved.task_id == "task123"

    def test_storage_get_nonexistent(self):
        storage = MemoryTaskStorage()
        result = storage.get("nonexistent")
        assert result is None

    def test_storage_delete(self):
        storage = MemoryTaskStorage()
        task = Task(
            task_id="task123",
            func_name="test_func"
        )
        storage.set(task)
        storage.delete("task123")
        assert storage.get("task123") is None


class TestTaskManager:
    """任务管理器测试"""

    def test_task_manager_creation(self):
        manager = TaskManager()
        assert manager is not None

    def test_submit_and_get_task(self):
        manager = TaskManager()
        task_id = manager.submit("process_chat", "hello", "session123")
        assert task_id is not None
        task = manager.get_task(task_id)
        assert task is not None

    def test_get_task_nonexistent(self):
        manager = TaskManager()
        result = manager.get_task("nonexistent")
        assert result is None

    def test_shutdown(self):
        manager = TaskManager()
        manager.shutdown()


class TestTaskManagerSingleton:
    """任务管理器单例测试"""

    def test_get_task_manager(self):
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        assert manager1 is manager2
