"""警告过滤器配置"""

import warnings

warnings.filterwarnings(
    "ignore",
    message="'asyncio.iscoroutinefunction' is deprecated",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message="Call to deprecated close",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    message="Deprecated",
    category=DeprecationWarning,
)

__all__ = []
