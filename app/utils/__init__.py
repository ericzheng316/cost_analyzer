"""
工具函数包

这个包包含了应用中使用的各种工具函数。
"""

from .resource_path import resource_path
from .error_handler import ErrorHandler

__all__ = ['resource_path', 'ErrorHandler']