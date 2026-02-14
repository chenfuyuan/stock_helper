import logging
import sys

from loguru import logger

from src.shared.config import settings


class InterceptHandler(logging.Handler):
    """
    拦截标准 logging 日志并转发到 Loguru
    """

    def emit(self, record):
        # 获取对应的 Loguru 日志级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找日志调用的原始位置
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """
    配置日志系统
    接管标准库 logging，统一使用 Loguru 输出

    配置格式：
    - 时间戳 (YYYY-MM-DD HH:mm:ss.SSS)
    - 日志级别 (DEBUG/INFO/WARN/ERROR)
    - 线程信息 (ID)
    - 模块名:函数名:行号
    - 日志消息
    """
    # 拦截所有 root logger 的日志
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    # 移除其他所有 logger 的 handler，并启用传播
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # 定义日志格式
    # 时间 | 级别 | 线程ID | 模块:函数:行号 | 消息
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>Thread-{thread.id}</cyan> | "
        "<magenta>{name}</magenta>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # 配置 Loguru
    # 在生产环境(prod)使用序列化(JSON)输出，便于日志收集系统解析
    # 在开发环境使用自定义格式输出
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "serialize": settings.ENVIRONMENT == "prod",
                "format": (log_format if settings.ENVIRONMENT != "prod" else "{message}"),
            }
        ]
    )
