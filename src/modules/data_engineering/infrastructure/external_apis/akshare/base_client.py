import asyncio
import time

from loguru import logger

# akshare 限速锁：全进程共享，确保 API 调用频率不超过限制
_akshare_rate_lock: asyncio.Lock | None = None
_akshare_last_call: float = 0.0


def _get_akshare_rate_lock() -> asyncio.Lock:
    """获取进程内共享的 akshare 限速锁"""
    global _akshare_rate_lock
    if _akshare_rate_lock is None:
        _akshare_rate_lock = asyncio.Lock()
    return _akshare_rate_lock


class AkShareBaseClient:
    """
    AkShare API 客户端基类
    封装限速和异步执行逻辑，子类专注于各自的数据转换
    """

    def __init__(self, request_interval: float = 0.3):
        """
        初始化 AkShare 客户端
        
        Args:
            request_interval: 请求间隔（秒），默认 0.3s，避免触发限流
        """
        self.request_interval = request_interval

    async def _run_in_executor(self, func, *args, **kwargs):
        """
        在默认线程池中执行同步函数，避免阻塞事件循环
        
        Args:
            func: 同步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _rate_limited_call(self, func, *args, **kwargs):
        """
        带限速的 akshare API 调用，确保不触发限流
        全进程共享限速锁，按配置的 request_interval 控制调用频率
        
        Args:
            func: 同步函数（通常是 akshare API 函数）
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            API 调用结果
        """
        global _akshare_last_call
        lock = _get_akshare_rate_lock()
        async with lock:
            now = time.monotonic()
            elapsed = now - _akshare_last_call
            if elapsed < self.request_interval and _akshare_last_call > 0:
                wait_time = self.request_interval - elapsed
                logger.debug(f"akshare 限速：等待 {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            result = await self._run_in_executor(func, *args, **kwargs)
            _akshare_last_call = time.monotonic()
            return result
