"""滑动窗口限速器"""

import asyncio
import time
from collections import deque
from typing import Deque


class SlidingWindowRateLimiter:
    """滑动窗口限速器（Sliding Window Log）
    
    维护精确的时间戳队列，在指定时间窗口内限制最大调用次数。
    相比固定间隔策略，允许突发调用，充分利用 API 配额。
    
    使用示例：
        limiter = SlidingWindowRateLimiter(max_calls=195, window_seconds=60.0)
        await limiter.acquire()  # 获取调用许可，必要时等待
    """

    def __init__(self, max_calls: int = 195, window_seconds: float = 60.0):
        """初始化滑动窗口限速器
        
        Args:
            max_calls: 窗口内最大调用次数，默认 195（预留安全余量）
            window_seconds: 时间窗口大小（秒），默认 60.0
        """
        self._max_calls = max_calls
        self._window = window_seconds
        self._timestamps: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取调用许可
        
        若窗口内已达上限，则等待最早的时间戳滑出窗口后再返回。
        此方法是协程安全的，多个并发调用会按顺序获取许可。
        """
        async with self._lock:
            now = time.monotonic()
            
            # 清除窗口外的旧时间戳
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()
            
            # 若已达上限，等待最早的时间戳滑出窗口
            if len(self._timestamps) >= self._max_calls:
                # 计算需要等待的时间：最早时间戳 + 窗口大小 - 当前时间
                wait_time = self._window - (now - self._timestamps[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # 等待后重新获取当前时间并清理过期时间戳
                    now = time.monotonic()
                    while self._timestamps and now - self._timestamps[0] >= self._window:
                        self._timestamps.popleft()
            
            # 记录本次调用时间戳
            self._timestamps.append(now)
