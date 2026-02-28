import asyncio
import time
import random
import functools
import logging

# Configure logger
logger = logging.getLogger(__name__)

def calculate_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current retry attempt (1-based)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
    """
    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
    
    if jitter:
        # Add random jitter between 0 and 100% of the delay
        delay = delay * random.uniform(0.5, 1.5)
        
    return delay

def async_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, exceptions: tuple = (Exception,)):
    """
    Decorator for async functions to retry on failure with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_retries + 2):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt > max_retries:
                        logger.exception(
                            "All %s retries failed for %s. Last error: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
                        raise last_exception
                    
                    delay = calculate_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        "%s failed (%s). Retrying in %.2fs... (Attempt %s/%s)",
                        func.__name__,
                        e,
                        delay,
                        attempt,
                        max_retries,
                    )
                    await asyncio.sleep(delay)
            
            return None # Should not be reached
        return wrapper
    return decorator

def sync_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, exceptions: tuple = (Exception,)):
    """
    Decorator for synchronous functions to retry on failure with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_retries + 2):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt > max_retries:
                        logger.exception(
                            "All %s retries failed for %s. Last error: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
                        raise last_exception
                    
                    delay = calculate_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        "%s failed (%s). Retrying in %.2fs... (Attempt %s/%s)",
                        func.__name__,
                        e,
                        delay,
                        attempt,
                        max_retries,
                    )
                    time.sleep(delay)
            
            return None # Should not be reached
        return wrapper
    return decorator
