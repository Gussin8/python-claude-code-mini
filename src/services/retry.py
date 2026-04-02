"""Retry mechanism with exponential backoff"""

import asyncio
import random
from typing import Callable, TypeVar, Any
from functools import wraps


T = TypeVar("T")


class RetryError(Exception):
    """重试失败错误"""

    def __init__(self, message: str, attempts: int, last_error: Exception = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


async def with_retry(
    func: Callable[..., T],
    *args,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception]] = (Exception,),
    **kwargs,
) -> T:
    """带重试的函数装饰器
    
    使用指数退避策略进行重试。
    
    Args:
        func: 要执行的异步函数
        args: 位置参数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型
        kwargs: 关键字参数
    
    Returns:
        函数执行结果
    
    Raises:
        RetryError: 重试失败
    
    示例:
        @with_retry(max_retries=3)
        async def fetch_data():
            ...
        
        # 或直接调用
        result = await with_retry(
            api_call,
            "arg1",
            key="value",
            max_retries=5
        )
    """

    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        except retryable_exceptions as e:
            last_exception = e
            
            # 如果是最后一次尝试，直接抛出
            if attempt == max_retries:
                raise RetryError(
                    f"Failed after {max_retries + 1} attempts",
                    attempts=max_retries + 1,
                    last_error=e,
                ) from e
            
            # 检查是否是可重试的错误
            if not _is_retryable_error(e):
                raise
            
            # 计算延迟
            delay = _calculate_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
            )
            
            # 等待后重试
            await asyncio.sleep(delay)
    
    # 不应该到达这里
    raise RetryError(
        f"Unexpected failure after {max_retries + 1} attempts",
        attempts=max_retries + 1,
        last_error=last_exception,
    )


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
) -> float:
    """计算重试延迟
    
    Args:
        attempt: 当前尝试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
    
    Returns:
        延迟时间（秒）
    """
    # 指数退避
    delay = base_delay * (exponential_base ** attempt)
    
    # 添加抖动
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    
    # 限制最大延迟
    return min(delay, max_delay)


def _is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试
    
    Args:
        error: 异常对象
    
    Returns:
        True 如果可重试
    """
    # 这些错误通常不可重试
    non_retryable = [
        "AuthenticationError",
        "PermissionDenied",
        "InvalidRequest",
    ]
    
    error_name = type(error).__name__
    return not any(name in error_name for name in non_retryable)


def retry_decorator(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        jitter: 是否添加随机抖动
    
    Returns:
        装饰器函数
    
    示例:
        @retry_decorator(max_retries=3)
        async def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_retry(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
                **kwargs,
            )
        return wrapper
    return decorator
