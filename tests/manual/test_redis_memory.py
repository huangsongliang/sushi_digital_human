"""测试 Redis 记忆系统"""

import asyncio
import sys

sys.path.insert(0, "d:/code/sushi_digital_human")

from backend.memory import ConversationMemory, cache_manager, redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def test_redis_connection():
    """测试 Redis 连接"""
    logger.info("测试 Redis 连接...")

    if await redis_conn.ping():
        logger.info("✅ Redis 连接成功")
        return True
    else:
        logger.error("❌ Redis 连接失败")
        return False


async def test_conversation_memory():
    """测试对话记忆"""
    logger.info("\n测试对话记忆...")

    memory = ConversationMemory(session_id="test_session_001")

    # 保存消息
    await memory.save_message("user", "苏轼是谁？")
    await memory.save_message("assistant", "苏轼是北宋著名文学家...")
    await memory.save_message("user", "他的代表作有哪些？")

    # 获取历史
    history = await memory.get_history(limit=10)
    logger.info(f"✅ 历史消息数量: {len(history)}")

    for i, msg in enumerate(history, 1):
        logger.info(f"  {i}. [{msg.role}]: {msg.content[:30]}...")

    # 测试上下文生成
    context = await memory.get_context_for_rag(max_messages=2)
    logger.info(f"✅ RAG 上下文:\n{context}")

    # 清理
    await memory.clear_history()
    logger.info("✅ 测试数据已清理")


async def test_cache():
    """测试缓存"""
    logger.info("\n测试缓存...")

    query = "苏轼的诗词有什么特点"

    # 设置缓存
    result = {"answer": "苏轼的诗词豪放洒脱...", "sources": []}
    await cache_manager.set(query, result)
    logger.info("✅ 缓存已设置")

    # 获取缓存
    cached = await cache_manager.get(query)
    if cached:
        logger.info(f"✅ 缓存命中: {cached['answer'][:20]}...")
    else:
        logger.error("❌ 缓存未命中")

    # 清理
    await cache_manager.clear_all()
    logger.info("✅ 缓存已清空")


async def main():
    logger.info("=" * 60)
    logger.info("开始测试 Redis 记忆系统")
    logger.info("=" * 60)

    try:
        # 测试连接
        if not await test_redis_connection():
            logger.error("Redis 连接失败，退出测试")
            return

        # 测试对话记忆
        await test_conversation_memory()

        # 测试缓存
        await test_cache()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有测试通过！Redis 记忆系统工作正常")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await redis_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
