"""
状态管理模块 - Store驱动架构的核心

这个模块实现了集中式状态管理，使用Dash的dcc.Store组件来存储应用状态。

核心理念：
    单向数据流：用户交互 → 更新Store → 监听Store的回调 → 更新UI

优势：
1. 解耦合 - Input和Output通过Store解耦
2. 可扩展 - 添加新功能只需修改Store结构
3. 可持久化 - Store可以使用session或local存储
4. 可调试 - 可以在浏览器DevTools中查看Store状态
5. 可测试 - 状态是纯JSON，易于测试

使用示例：
    from app.state_manager import StateManager, create_all_stores

    # 在app.layout中添加所有Store
    app.layout = html.Div([
        *create_all_stores(),  # 一次性创建所有Store
        # ... 其他组件
    ])

    # 在回调中使用
    @app.callback(
        Output(ComponentIDs.Store.FILTER_STATE, 'data'),
        Input('some-button', 'n_clicks')
    )
    def update_filters(n_clicks):
        return StateManager.create_filter_state(filters={'列名': 'value'})
"""

from dash import dcc
from datetime import datetime
from typing import Dict, Any, Optional, List


class StateManager:
    """
    状态管理器 - 提供创建和验证Store数据的工具方法
    """

    # ===========================================
    # 筛选器状态 (FILTER_STATE)
    # ===========================================

    @staticmethod
    def create_filter_state(
        filters: Optional[Dict[str, Dict[str, Any]]] = None,
        last_updated: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建筛选器状态数据

        参数：
            filters: 筛选器字典，格式：
                {
                    '列名': {
                        'value': 筛选值,
                        'method': 'exact' | 'fuzzy'
                    }
                }
            last_updated: 最后更新时间（ISO格式），默认为当前时间

        返回：
            符合FILTER_STATE结构的字典

        示例：
            >>> StateManager.create_filter_state({
            ...     '项目名称': {'value': '地面', 'method': 'fuzzy'},
            ...     '功能区_L1': {'value': '装饰工程', 'method': 'exact'}
            ... })
        """
        return {
            'filters': filters or {},
            'last_updated': last_updated or datetime.now().isoformat()
        }

    @staticmethod
    def get_empty_filter_state() -> Dict[str, Any]:
        """获取空的筛选器状态"""
        return StateManager.create_filter_state()

    # ===========================================
    # 图表配置状态 (CHART_CONFIG)
    # ===========================================

    @staticmethod
    def create_chart_config(
        chart_type: str = 'bar',
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        view_options: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        创建图表配置数据

        参数：
            chart_type: 图表类型 ('bar', 'pie', 'scatter', 'line', 'histogram', 'box')
            x_axis: X轴列名
            y_axis: Y轴列名
            view_options: 视图选项，格式：
                {
                    'TRUNCATE': bool,  # 是否剔除长描述列
                    'AGGREGATE': bool  # 是否合并同类项
                }

        返回：
            符合CHART_CONFIG结构的字典
        """
        if view_options is None:
            view_options = {'TRUNCATE': False, 'AGGREGATE': False}

        return {
            'type': chart_type,
            'x_axis': x_axis,
            'y_axis': y_axis,
            'view_options': view_options
        }

    @staticmethod
    def get_default_chart_config() -> Dict[str, Any]:
        """获取默认图表配置"""
        return StateManager.create_chart_config()

    # ===========================================
    # 数据状态 (DATA_STATE)
    # ===========================================

    @staticmethod
    def create_data_state(
        current_file: Optional[str] = None,
        staged_file: Optional[str] = None,
        data_loaded: bool = False,
        total_rows: int = 0,
        total_columns: int = 0,
        file_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建数据状态

        参数：
            current_file: 当前已提交的文件路径
            staged_file: 暂存的文件路径（预览中）
            data_loaded: 是否已加载数据
            total_rows: 数据总行数
            total_columns: 数据总列数
            file_timestamp: 文件处理时间戳

        返回：
            符合DATA_STATE结构的字典
        """
        return {
            'current_file': current_file,
            'staged_file': staged_file,
            'data_loaded': data_loaded,
            'total_rows': total_rows,
            'total_columns': total_columns,
            'file_timestamp': file_timestamp or datetime.now().isoformat()
        }

    @staticmethod
    def get_empty_data_state() -> Dict[str, Any]:
        """获取空的数据状态"""
        return StateManager.create_data_state()

    # ===========================================
    # UI状态 (UI_STATE)
    # ===========================================

    @staticmethod
    def create_ui_state(
        modal_open: bool = False,
        loading: bool = False,
        error_message: Optional[str] = None,
        success_message: Optional[str] = None,
        warning_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建UI状态

        参数：
            modal_open: 模态框是否打开
            loading: 是否显示加载动画
            error_message: 错误消息
            success_message: 成功消息
            warning_message: 警告消息

        返回：
            符合UI_STATE结构的字典
        """
        return {
            'modal_open': modal_open,
            'loading': loading,
            'error_message': error_message,
            'success_message': success_message,
            'warning_message': warning_message
        }

    @staticmethod
    def get_default_ui_state() -> Dict[str, Any]:
        """获取默认UI状态"""
        return StateManager.create_ui_state()

    # ===========================================
    # 导入流程状态 (IMPORT_STATE)
    # ===========================================

    @staticmethod
    def create_import_state(
        stage: str = 'idle',  # 'idle', 'uploaded', 'previewing', 'committing'
        current_file_path: Optional[str] = None,
        original_filename: Optional[str] = None,
        sheet_names: Optional[List[str]] = None,
        selected_sheet: Optional[str] = None,
        preview_data_available: bool = False,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建导入流程状态

        参数：
            stage: 当前阶段
                - 'idle': 空闲
                - 'uploaded': 已上传文件
                - 'previewing': 预览中
                - 'committing': 提交中
            current_file_path: 当前文件路径
            original_filename: 原始文件名
            sheet_names: 工作表名称列表
            selected_sheet: 选中的工作表
            preview_data_available: 是否有预览数据
            error: 错误消息

        返回：
            符合IMPORT_STATE结构的字典
        """
        return {
            'stage': stage,
            'current_file_path': current_file_path,
            'original_filename': original_filename,
            'sheet_names': sheet_names or [],
            'selected_sheet': selected_sheet,
            'preview_data_available': preview_data_available,
            'error': error,
            'last_updated': datetime.now().isoformat()
        }

    @staticmethod
    def get_initial_import_state() -> Dict[str, Any]:
        """获取初始导入状态"""
        return StateManager.create_import_state()


# ===========================================
# Store组件创建函数
# ===========================================

def create_all_stores() -> List[dcc.Store]:
    """
    创建所有需要的Store组件

    这个函数应该在app.layout中调用，用于一次性创建所有Store。

    返回：
        dcc.Store组件列表

    使用示例：
        app.layout = html.Div([
            *create_all_stores(),
            # ... 其他布局组件
        ])
    """
    from app.component_ids import ComponentIDs

    return [
        # 筛选器状态 (session存储，页面刷新保留)
        dcc.Store(
            id=ComponentIDs.Store.FILTER_STATE,
            storage_type='session',
            data=StateManager.get_empty_filter_state()
        ),

        # 图表配置 (session存储)
        dcc.Store(
            id=ComponentIDs.Store.CHART_CONFIG,
            storage_type='session',
            data=StateManager.get_default_chart_config()
        ),

        # 数据状态 (session存储)
        dcc.Store(
            id=ComponentIDs.Store.DATA_STATE,
            storage_type='session',
            data=StateManager.get_empty_data_state()
        ),

        # UI状态 (memory存储，页面刷新清空)
        dcc.Store(
            id=ComponentIDs.Store.UI_STATE,
            storage_type='memory',
            data=StateManager.get_default_ui_state()
        ),

        # 导入流程状态 (memory存储)
        dcc.Store(
            id=ComponentIDs.Store.IMPORT_STATE,
            storage_type='memory',
            data=StateManager.get_initial_import_state()
        ),

        # 保留旧的ETL状态存储以保持兼容性
        dcc.Store(
            id=ComponentIDs.Store.ETL_STATUS,
            storage_type='session'
        )
    ]


# ===========================================
# 辅助函数
# ===========================================

def merge_filters(
    existing_filters: Dict[str, Dict[str, Any]],
    new_filters: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    合并筛选器字典

    参数：
        existing_filters: 现有筛选器
        new_filters: 新的筛选器

    返回：
        合并后的筛选器字典（新筛选器会覆盖同名的旧筛选器）

    示例：
        >>> existing = {'列A': {'value': 'old', 'method': 'exact'}}
        >>> new = {'列B': {'value': 'new', 'method': 'fuzzy'}}
        >>> merge_filters(existing, new)
        {'列A': {'value': 'old', 'method': 'exact'},
         '列B': {'value': 'new', 'method': 'fuzzy'}}
    """
    result = existing.copy()
    result.update(new_filters)
    return result


def clear_empty_filters(filters: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    清除空值的筛选器

    参数：
        filters: 筛选器字典

    返回：
        清除空值后的筛选器字典

    示例：
        >>> filters = {
        ...     '列A': {'value': 'data', 'method': 'exact'},
        ...     '列B': {'value': None, 'method': 'exact'},
        ...     '列C': {'value': '', 'method': 'fuzzy'}
        ... }
        >>> clear_empty_filters(filters)
        {'列A': {'value': 'data', 'method': 'exact'}}
    """
    return {
        key: value
        for key, value in filters.items()
        if value.get('value') not in (None, '', [])
    }
