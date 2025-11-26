"""
统一错误处理模块

提供标准化的错误、警告、成功消息展示和异常处理装饰器。

优势：
1. 统一的UI风格 - 所有消息使用相同的组件和样式
2. 简化开发 - 一个函数调用即可创建消息组件
3. 易于维护 - 修改样式时只需修改一处
4. 异常处理 - 装饰器自动捕获并显示异常

使用示例：
    from app.utils.error_handler import ErrorHandler

    # 在回调中返回错误消息
    def my_callback(...):
        if some_error:
            return ErrorHandler.create_error_alert("文件未找到")

    # 使用装饰器自动处理异常
    @app.callback(...)
    @ErrorHandler.handle_callback_error("数据导入")
    def upload_file(...):
        # 如果这里抛出异常，会自动捕获并显示友好的错误消息
        process_file()
"""

from dash import html
import dash_bootstrap_components as dbc
from typing import Optional, Union
import traceback
from functools import wraps


class ErrorHandler:
    """统一的错误处理和消息展示工具"""

    # ===========================================
    # 消息创建方法
    # ===========================================

    @staticmethod
    def create_error_alert(
        message: str,
        title: str = "错误",
        dismissable: bool = True
    ) -> dbc.Alert:
        """
        创建标准化的错误提示

        参数：
            message: 错误消息内容
            title: 标题，默认"错误"
            dismissable: 是否可关闭，默认True

        返回：
            Dash Bootstrap Alert组件

        示例：
            >>> ErrorHandler.create_error_alert("文件不存在")
        """
        return dbc.Alert(
            [
                html.H5(title, className="alert-heading"),
                html.P(message)
            ],
            color="danger",
            dismissable=dismissable,
            className="mb-3"
        )

    @staticmethod
    def create_warning_alert(
        message: str,
        title: str = "警告",
        dismissable: bool = True
    ) -> dbc.Alert:
        """
        创建标准化的警告提示

        参数：
            message: 警告消息内容
            title: 标题，默认"警告"
            dismissable: 是否可关闭，默认True

        返回：
            Dash Bootstrap Alert组件

        示例：
            >>> ErrorHandler.create_warning_alert("数据可能不完整")
        """
        return dbc.Alert(
            [
                html.H5(title, className="alert-heading"),
                html.P(message)
            ],
            color="warning",
            dismissable=dismissable,
            className="mb-3"
        )

    @staticmethod
    def create_success_alert(
        message: str,
        title: str = "成功",
        dismissable: bool = True
    ) -> dbc.Alert:
        """
        创建标准化的成功提示

        参数：
            message: 成功消息内容
            title: 标题，默认"成功"
            dismissable: 是否可关闭，默认True

        返回：
            Dash Bootstrap Alert组件

        示例：
            >>> ErrorHandler.create_success_alert("文件已成功保存")
        """
        return dbc.Alert(
            [
                html.H5(title, className="alert-heading"),
                html.P(message)
            ],
            color="success",
            dismissable=dismissable,
            className="mb-3"
        )

    @staticmethod
    def create_info_alert(
        message: str,
        title: str = "提示",
        dismissable: bool = True
    ) -> dbc.Alert:
        """
        创建标准化的信息提示

        参数：
            message: 信息消息内容
            title: 标题，默认"提示"
            dismissable: 是否可关闭，默认True

        返回：
            Dash Bootstrap Alert组件

        示例：
            >>> ErrorHandler.create_info_alert("正在处理中，请稍候...")
        """
        return dbc.Alert(
            [
                html.H5(title, className="alert-heading"),
                html.P(message)
            ],
            color="info",
            dismissable=dismissable,
            className="mb-3"
        )

    # ===========================================
    # 旧版兼容方法（保持向后兼容）
    # ===========================================

    @staticmethod
    def create_error_div(message: str) -> html.Div:
        """
        创建简单的错误Div（旧版兼容）

        参数：
            message: 错误消息

        返回：
            红色文字的html.Div组件
        """
        return html.Div(message, style={'color': 'red'})

    @staticmethod
    def create_success_div(message: str) -> html.Div:
        """
        创建简单的成功Div（旧版兼容）

        参数：
            message: 成功消息

        返回：
            绿色文字的html.Div组件
        """
        return html.Div(message, style={'color': 'green'})

    @staticmethod
    def create_warning_div(message: str) -> html.Div:
        """
        创建简单的警告Div（旧版兼容）

        参数：
            message: 警告消息

        返回：
            橙色文字的html.Div组件
        """
        return html.Div(message, style={'color': 'orange'})

    # ===========================================
    # 异常处理装饰器
    # ===========================================

    @staticmethod
    def handle_callback_error(callback_name: str, show_traceback: bool = False):
        """
        回调函数异常处理装饰器

        自动捕获回调函数中的异常，并返回友好的错误消息组件。

        参数：
            callback_name: 回调名称，用于日志和错误消息
            show_traceback: 是否在错误消息中显示堆栈跟踪（开发环境建议True）

        返回：
            装饰器函数

        使用示例：
            @app.callback(...)
            @ErrorHandler.handle_callback_error("文件上传", show_traceback=True)
            def upload_file(...):
                # 如果这里抛出异常，会自动捕获
                raise ValueError("文件格式错误")
                # 用户会看到友好的错误消息，而不是应用崩溃
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 打印到控制台（用于调试）
                    print(f"[{callback_name}] 发生异常: {str(e)}")
                    traceback.print_exc()

                    # 构建错误消息
                    error_message = f"{str(e)}"
                    if show_traceback:
                        tb_str = traceback.format_exc()
                        error_message = html.Div([
                            html.P(str(e)),
                            html.Details([
                                html.Summary("点击查看详细堆栈信息"),
                                html.Pre(
                                    tb_str,
                                    style={
                                        'backgroundColor': '#f5f5f5',
                                        'padding': '10px',
                                        'border': '1px solid #ddd',
                                        'borderRadius': '4px',
                                        'fontSize': '12px',
                                        'overflow': 'auto'
                                    }
                                )
                            ])
                        ])

                    # 返回错误Alert组件
                    return ErrorHandler.create_error_alert(
                        error_message,
                        f"{callback_name} 错误"
                    )
            return wrapper
        return decorator

    @staticmethod
    def safe_callback(default_return=None):
        """
        安全回调装饰器 - 静默捕获异常并返回默认值

        用于不需要显示错误消息的场景，只是防止回调崩溃。

        参数：
            default_return: 异常时返回的默认值

        使用示例：
            @app.callback(...)
            @ErrorHandler.safe_callback(default_return={'layout': {'title': '加载失败'}})
            def update_graph(...):
                # 如果抛出异常，会返回默认图表
                return risky_operation()
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[{func.__name__}] 静默捕获异常: {str(e)}")
                    traceback.print_exc()
                    return default_return
            return wrapper
        return decorator


# ===========================================
# 辅助函数
# ===========================================

def format_exception_message(e: Exception) -> str:
    """
    格式化异常消息，使其更易读

    参数：
        e: 异常对象

    返回：
        格式化后的错误消息字符串

    示例：
        >>> try:
        ...     raise FileNotFoundError("test.xlsx not found")
        ... except Exception as e:
        ...     print(format_exception_message(e))
        文件未找到: test.xlsx not found
    """
    exception_type = type(e).__name__

    # 常见异常类型的友好名称映射
    friendly_names = {
        'FileNotFoundError': '文件未找到',
        'ValueError': '数值错误',
        'KeyError': '键不存在',
        'TypeError': '类型错误',
        'AttributeError': '属性错误',
        'IndexError': '索引错误',
        'PermissionError': '权限错误',
        'IOError': '输入输出错误',
        'OSError': '系统错误'
    }

    friendly_type = friendly_names.get(exception_type, exception_type)
    return f"{friendly_type}: {str(e)}"


def validate_not_none(value, field_name: str):
    """
    验证值不为None，否则抛出异常

    参数：
        value: 要验证的值
        field_name: 字段名称（用于错误消息）

    抛出：
        ValueError: 如果值为None

    使用示例：
        def process_data(df):
            validate_not_none(df, "数据框")
            # 继续处理...
    """
    if value is None:
        raise ValueError(f"缺少必需参数: {field_name}")


def validate_not_empty(value, field_name: str):
    """
    验证值不为空（None, '', [], {}等），否则抛出异常

    参数：
        value: 要验证的值
        field_name: 字段名称（用于错误消息）

    抛出：
        ValueError: 如果值为空

    使用示例:
        def upload_file(filename):
            validate_not_empty(filename, "文件名")
            # 继续处理...
    """
    if not value:
        raise ValueError(f"{field_name} 不能为空")