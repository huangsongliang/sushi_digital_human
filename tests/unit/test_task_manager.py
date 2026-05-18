"""任务管理器单元测试"""
import time
import pytest
from backend.utils.task_manager import Task, TaskStatus, MemoryTaskStorage, TaskManager, get_task_manager


class TestTask:
    """任务对象测试"""
    
    def test_task_creation(self):
        task = Task(task_id="test-123", func_name="test_func")
        assert task.task_id == "test-123"
        assert task.func_name == "test_func"
        assert task.status == TaskStatus.PENDING
        assert task.created_at > 0
    
    def test_task_duration(self):
        task = Task(task_id="test-123", func_name="test_func")
        time.sleep(0.1)
        assert task.duration >= 0.1
        
        task.completed_at = time.time()
        completed_duration = task.duration
        time.sleep(0.1)
        assert task.duration == completed_duration
    
    def test_task_is_complete(self):
        task = Task(task_id="test-123", func_name="test_func")
        assert not task.is_complete
        
        task.status = TaskStatus.COMPLETED
        assert task.is_complete
        
        task.status = TaskStatus.FAILED
        assert task.is_complete
        
        task.status = TaskStatus.PROCESSING
        assert not task.is_complete
    
    def test_task_to_dict(self):
        task = Task(task_id="test-123", func_name="test_func")
        task.status = TaskStatus.COMPLETED
        task.result = {"key": "value"}
        task.error = ""
        
        task_dict = task.to_dict()
        assert task_dict["task_id"] == "test-123"
        assert task_dict["func_name"] == "test_func"
        assert task_dict["status"] == "completed"
        assert task_dict["result"] == {"key": "value"}
    
    def test_task_from_dict(self):
        data = {
            "task_id": "test-123",
            "func_name": "test_func",
            "status": "completed",
            "result": {"key": "value"},
            "error": "",
            "created_at": 1234567890.0,
            "started_at": 1234567891.0,
            "completed_at": 1234567900.0
        }
        
        task = Task.from_dict(data)
        assert task.task_id == "test-123"
        assert task.func_name == "test_func"
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"key": "value"}


class TestMemoryTaskStorage:
    """内存任务存储测试"""
    
    def test_storage_set_and_get(self):
        storage = MemoryTaskStorage()
        task = Task(task_id="test-123", func_name="test_func")
        
        storage.set(task)
        retrieved = storage.get("test-123")
        
        assert retrieved is not None
        assert retrieved.task_id == "test-123"
    
    def test_storage_get_nonexistent(self):
        storage = MemoryTaskStorage()
        result = storage.get("nonexistent")
        assert result is None
    
    def test_storage_delete(self):
        storage = MemoryTaskStorage()
        task = Task(task_id="test-123", func_name="test_func")
        
        storage.set(task)
        assert storage.get("test-123") is not None
        
        storage.delete("test-123")
        assert storage.get("test-123") is None


class TestTaskManager:
    """任务管理器测试"""
    
    def test_task_manager_creation(self):
        manager = TaskManager(max_workers=5)
        assert manager is not None
    
    def test_submit_and_get_task(self):
        manager = TaskManager(max_workers=5)
        
        def test_func(a, b):
            return a + b
        
        manager.functions['test_func'] = test_func
        
        task_id = manager.submit('test_func', 1, 2)
        assert task_id is not None
        
        # 等待任务完成
        time.sleep(0.5)
        
        task = manager.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.COMPLETED
        assert task.result == 3
    
    def test_submit_failed_task(self):
        manager = TaskManager(max_workers=5)
        
        def failing_func():
            raise ValueError("Test error")
        
        manager.functions['failing_func'] = failing_func
        
        task_id = manager.submit('failing_func')
        
        time.sleep(0.5)
        
        task = manager.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert "Test error" in task.error
    
    def test_get_task_nonexistent(self):
        manager = TaskManager(max_workers=5)
        task = manager.get_task("nonexistent")
        assert task is None
    
    def test_shutdown(self):
        manager = TaskManager(max_workers=5)
        manager.shutdown()
        assert not manager._running


class TestTaskManagerSingleton:
    """任务管理器单例测试"""
    
    def test_get_task_manager(self):
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        
        assert manager1 is manager2