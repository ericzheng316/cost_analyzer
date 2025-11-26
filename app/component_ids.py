"""
组件ID集中管理模块

这个模块集中定义了应用中所有Dash组件的ID常量，避免硬编码字符串。

优势：
1. IDE自动补全 - 输入 ComponentIDs. 后会显示所有可用ID
2. 类型安全 - 拼写错误在编码时发现，而非运行时
3. 易于重构 - 重命名时只需修改一处
4. 可追溯性 - 可以查找所有使用某个ID的地方

使用示例：
    from app.component_ids import ComponentIDs

    @app.callback(
        Output(ComponentIDs.Visualizer.MAIN_GRAPH, 'figure'),
        Input(ComponentIDs.Visualizer.APPLY_FILTERS_BTN, 'n_clicks')
    )
    def update_graph(...):
        pass
"""


class ComponentIDs:
    """所有组件ID的命名空间"""

    # ===========================================
    # 主布局相关
    # ===========================================
    TABS_MAIN = 'tabs-main'
    TABS_CONTENT = 'tabs-content'

    # ===========================================
    # 数据导入模块
    # ===========================================
    class Importer:
        """数据导入选项卡的所有组件ID"""

        # 文件上传相关
        UPLOAD_DATA = 'upload-data'
        TEST_IMPORT_BTN = 'test-import-button'

        # 输出容器
        OUTPUT_CONTAINER = 'importer-output-container'
        PREVIEW_CONTAINER = 'importer-preview-container'

        # 工作表选择
        SHEET_DROPDOWN = 'sheet-dropdown'
        PARSE_BUTTON = 'parse-sheet-button'

        # 预览表格
        PREVIEW_TABLE = 'preview-table'

        # 确认/丢弃按钮
        COMMIT_BUTTON = 'commit-button'
        DISCARD_BUTTON = 'discard-button'

        # Loading组件
        LOADING = 'loading-importer'

    # ===========================================
    # 可视化模块
    # ===========================================
    class Visualizer:
        """可视化选项卡的所有组件ID"""

        # 主图表
        MAIN_GRAPH = 'main-interactive-graph'

        # 图表配置
        CHART_TYPE_DROPDOWN = 'chart-type-dropdown'
        X_AXIS_DROPDOWN = 'x-axis-dropdown'
        Y_AXIS_DROPDOWN = 'y-axis-dropdown'

        # 筛选和视图控制
        APPLY_FILTERS_BTN = 'apply-filters-button'
        VIEW_SWITCHER = 'view-switcher-checklist'
        AGGREGATION_CHECKER = 'aggregation-checklist'

        # 动态筛选器（使用Pattern-Matching）
        # 这些不是固定ID，而是ID模式
        FILTER_INPUT_TYPE = 'filter-input'
        FILTER_DROPDOWN_TYPE = 'filter-dropdown'

    # ===========================================
    # 日志查看模块
    # ===========================================
    class Logger:
        """日志选项卡的所有组件ID"""

        LOG_TABLE = 'log-table'

    # ===========================================
    # 模态框（钻取功能）
    # ===========================================
    class Modal:
        """数据钻取模态框的所有组件ID"""

        DRILL_DOWN = 'drill-down-modal'
        HEADER = 'modal-header'
        BODY = 'modal-body'
        CLOSE_BTN = 'close-modal-button'

    # ===========================================
    # 数据存储（Store组件）
    # ===========================================
    class Store:
        """所有dcc.Store组件的ID"""

        # 筛选器状态
        FILTER_STATE = 'store-filter-state'

        # 图表配置
        CHART_CONFIG = 'store-chart-config'

        # 数据状态
        DATA_STATE = 'store-data-state'

        # UI状态
        UI_STATE = 'store-ui-state'

        # 导入流程状态
        IMPORT_STATE = 'store-import-state'

        # 旧的ETL状态存储（保持兼容）
        ETL_STATUS = 'etl-status-store'


# ===========================================
# 辅助函数
# ===========================================

def create_filter_id(column_name: str, filter_type: str = 'dropdown') -> dict:
    """
    创建Pattern-Matching筛选器的ID字典

    参数：
        column_name: 列名
        filter_type: 'input' 或 'dropdown'

    返回：
        符合Dash Pattern-Matching格式的ID字典

    示例：
        >>> create_filter_id('项目名称', 'input')
        {'type': 'filter-input', 'index': '项目名称'}
    """
    if filter_type == 'input':
        type_str = ComponentIDs.Visualizer.FILTER_INPUT_TYPE
    elif filter_type == 'dropdown':
        type_str = ComponentIDs.Visualizer.FILTER_DROPDOWN_TYPE
    else:
        raise ValueError(f"未知的筛选器类型: {filter_type}")

    return {'type': type_str, 'index': column_name}
