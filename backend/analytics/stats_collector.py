"""使用统计和分析模块"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class StatsCollector:
    """统计收集器"""

    def __init__(self):
        pass

    def track_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ):
        """跟踪用户事件"""
        try:
            db.execute(
                """
                INSERT INTO user_analytics (id, user_id, event_type, event_data, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()),
                    user_id,
                    event_type,
                    str(event_data) if event_data else None,
                    datetime.now(),
                ),
            )
            db.commit()

        except Exception as e:
            logger.error(f"跟踪事件失败: {str(e)}")

    def get_user_stats(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """获取用户统计"""
        try:
            start_time = datetime.now() - timedelta(days=days)

            stats = {}

            result = db.execute(
                """
                SELECT COUNT(*) FROM user_analytics
                WHERE user_id = %s AND created_at >= %s
                """,
                (user_id, start_time),
            )
            stats["total_events"] = result.fetchone()[0]

            result = db.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM user_analytics
                WHERE user_id = %s AND created_at >= %s
                GROUP BY event_type
                """,
                (user_id, start_time),
            )
            stats["events_by_type"] = {row[0]: row[1] for row in result.fetchall()}

            result = db.execute(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM user_analytics
                WHERE user_id = %s AND created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (user_id, start_time),
            )
            stats["daily_usage"] = [{"date": str(row[0]), "count": row[1]} for row in result.fetchall()]

            return stats

        except Exception as e:
            logger.error(f"获取用户统计失败: {str(e)}")
            return {}

    def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取系统统计"""
        try:
            start_time = datetime.now() - timedelta(days=days)

            stats = {}

            result = db.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM user_analytics
                WHERE created_at >= %s
                """,
                (start_time,),
            )
            stats["active_users"] = result.fetchone()[0]

            result = db.execute(
                """
                SELECT COUNT(*) FROM user_analytics
                WHERE created_at >= %s
                """,
                (start_time,),
            )
            stats["total_events"] = result.fetchone()[0]

            result = db.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM user_analytics
                WHERE created_at >= %s
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
                """,
                (start_time,),
            )
            stats["top_events"] = [{"type": row[0], "count": row[1]} for row in result.fetchall()]

            return stats

        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return {}


_stats_collector: Optional[StatsCollector] = None


def get_stats_collector() -> StatsCollector:
    """获取统计收集器实例"""
    global _stats_collector
    if _stats_collector is None:
        _stats_collector = StatsCollector()
        logger.info("统计收集器已初始化")
    return _stats_collector
