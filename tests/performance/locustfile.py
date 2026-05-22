"""
Locust性能测试
测试系统负载能力
"""

from locust import HttpUser, task, between, tag


class SystemUser(HttpUser):
    """模拟用户行为"""
    
    wait_time = between(1, 3)  # 1-3秒之间的等待时间
    
    @tag("health")
    @task(3)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")
    
    @tag("chat")
    @task(2)
    def chat_request(self):
        """聊天请求"""
        response = self.client.post(
            "/api/chat",
            json={"message": "你好，请介绍一下"},
        )
    
    @tag("agent")
    @task(1)
    def agent_chat(self):
        """Agent聊天"""
        response = self.client.post(
            "/agent/chat",
            json={"query": "你好"},
        )
    
    @tag("summary")
    @task(1)
    def summarize_text(self):
        """文本总结"""
        response = self.client.post(
            "/summary/text",
            json={
                "content": "这是一段需要总结的文本内容。" * 10,
                "type": "brief"
            },
        )
    
    @tag("docs")
    @task(1)
    def get_alerts_summary(self):
        """获取告警摘要"""
        response = self.client.get("/alerts/summary")
    
    def on_start(self):
        """用户开始时执行"""
        pass
    
    def on_stop(self):
        """用户停止时执行"""
        pass