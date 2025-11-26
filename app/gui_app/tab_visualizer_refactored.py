"""
可视化模块 - 重构版（使用Store驱动架构）

重构目标：
1. 解决参数爆炸问题（从9个参数降到1-2个）
2. 使用Store作为中间层解耦Input和Output
3. 拆分成多个小回调，每个只做一件事
4. 使用ComponentIDs常量避免魔法字符串
5. 统一错误处理

架构对比：
    重构前：9个State → 1个巨大回调 → 直接更新图表
    重构后：多个Input → 更新Store → 监听Store → 更新图表

优势：
- 添加新筛选器只需修改Store结构，无需修改回调签名
- 每个回调职责单一，易于理解和测试
- 状态可持久化（session存储）
- 支持撤销/重做等高级功能
"""

import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import numpy as np

# 导入新的基础设施
from app.component_ids import ComponentIDs, create_filter_id
from app.state_manager import StateManager
from app.utils.error_handler import ErrorHandler

# 导入统一的可视化引擎（保持不变）
from app.analysis.visualizer import get_figure


# ===========================================
# 1. 布局创建函数（使用ComponentIDs）
# ===========================================

def create_visualizer_layout(df):
    """
    根据提供的数据帧创建可视化选项卡的布局

    参数：
        df: pandas DataFrame

    返回：
        Dash布局组件
    """
    if df is None or df.empty:
        return html.Div(
            "无可用数据，请先在「数据导入与处理」选项卡中导入数据。",
            className="text-center p-5"
        )

    all_columns = df.columns.tolist()
    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()

    # 动态生成筛选器（使用create_filter_id辅助函数）
    filters = []
    for col in all_columns:
        if col == '项目名称':
            # 文本输入筛选器（模糊搜索）
            filters.append(
                html.Div([
                    html.Label(f'{col} (模糊搜索)', className="form-label"),
                    dcc.Input(
                        id=create_filter_id(col, 'input'),  # 使用辅助函数创建ID
                        type='text',
                        className="form-control"
                    )
                ], className="mb-3")
            )
        elif df[col].dtype == 'object' and 1 < df[col].nunique() < 50:
            # 下拉筛选器
            options = [{'label': str(i), 'value': i} for i in df[col].unique() if i]
            filters.append(
                html.Div([
                    html.Label(col, className="form-label"),
                    dcc.Dropdown(
                        id=create_filter_id(col, 'dropdown'),  # 使用辅助函数
                        options=options,
                        className="form-select"
                    )
                ], className="mb-3")
            )

    # 视图选项
    view_switcher = dcc.Checklist(
        id=ComponentIDs.Visualizer.VIEW_SWITCHER,  # 使用常量
        options=[{'label': '剔除长描述列', 'value': 'TRUNCATE'}],
        value=[],
        className="form-check"
    )

    agg_switcher = dcc.Checklist(
        id=ComponentIDs.Visualizer.AGGREGATION_CHECKER,  # 使用常量
        options=[{'label': '合并同类项(仅条形图)', 'value': 'AGGREGATE'}],
        value=[],
        className="form-check"
    )

    # 完整布局
    return html.Div([
        html.Div([
            # 左侧筛选面板
            html.Div([
                html.H3('高级筛选器', className="mb-3"),
                *filters,
                html.Hr(),
                view_switcher,
                agg_switcher,
                html.Hr(),
                html.Button(
                    '应用并更新图表',
                    id=ComponentIDs.Visualizer.APPLY_FILTERS_BTN,  # 使用常量
                    className="btn btn-primary w-100",
                    style={'marginTop': '15px'}
                )
            ], style={'width': '25%', 'padding': '10px'}),

            # 右侧图表工作室
            html.Div([
                html.H3('图表工作室', className="mb-3"),
                html.Div([
                    dcc.Dropdown(
                        id=ComponentIDs.Visualizer.CHART_TYPE_DROPDOWN,  # 使用常量
                        options=[
                            {'label': '条形图', 'value': 'bar'},
                            {'label': '饼图', 'value': 'pie'},
                            {'label': '散点图', 'value': 'scatter'},
                            {'label': '折线图', 'value': 'line'},
                            {'label': '直方图', 'value': 'histogram'},
                            {'label': '箱形图', 'value': 'box'}
                        ],
                        value='bar',
                        className="mb-2"
                    ),
                    dcc.Dropdown(
                        id=ComponentIDs.Visualizer.X_AXIS_DROPDOWN,  # 使用常量
                        options=[{'label': i, 'value': i} for i in all_columns],
                        placeholder="选择X轴",
                        className="mb-2"
                    ),
                    dcc.Dropdown(
                        id=ComponentIDs.Visualizer.Y_AXIS_DROPDOWN,  # 使用常量
                        options=[{'label': i, 'value': i} for i in numeric_columns],
                        placeholder="选择Y轴",
                        className="mb-2"
                    ),
                ]),
                dcc.Graph(
                    id=ComponentIDs.Visualizer.MAIN_GRAPH,  # 使用常量
                    style={'height': '80vh'}
                )
            ], style={'width': '75%', 'padding': '10px'})
        ], style={'display': 'flex'})
    ])


# ===========================================
# 2. 回调函数注册（Store驱动架构）
# ===========================================

def register_visualizer_callbacks(app, controller):
    """
    注册所有与可视化相关的回调

    重构策略：
    1. 回调A: 收集筛选器值 → 更新FILTER_STATE Store
    2. 回调B: 收集图表配置 → 更新CHART_CONFIG Store
    3. 回调C: 监听两个Store → 渲染图表

    这样做的好处：
    - 添加新筛选器只需修改回调A的逻辑，无需修改签名
    - 每个回调职责单一
    - Store可以被多个回调监听
    """

    # ---------------------------------------
    # 回调A: 收集筛选器值 → 更新Store
    # ---------------------------------------
    @app.callback(
        Output(ComponentIDs.Store.FILTER_STATE, 'data'),
        Input(ComponentIDs.Visualizer.APPLY_FILTERS_BTN, 'n_clicks'),
        [State({'type': ComponentIDs.Visualizer.FILTER_INPUT_TYPE, 'index': dash.ALL}, 'value'),
         State({'type': ComponentIDs.Visualizer.FILTER_DROPDOWN_TYPE, 'index': dash.ALL}, 'value'),
         State({'type': ComponentIDs.Visualizer.FILTER_INPUT_TYPE, 'index': dash.ALL}, 'id'),
         State({'type': ComponentIDs.Visualizer.FILTER_DROPDOWN_TYPE, 'index': dash.ALL}, 'id')],
        prevent_initial_call=True
    )
    @ErrorHandler.handle_callback_error("筛选器更新", show_traceback=True)
    def update_filter_store(n_clicks, input_values, dropdown_values, input_ids, dropdown_ids):
        """
        只负责收集所有筛选器的值并打包成字典，存入Store

        职责：
        - 收集文本输入筛选器的值
        - 收集下拉筛选器的值
        - 打包成统一格式：{'列名': {'value': xx, 'method': 'fuzzy/exact'}}
        - 存入FILTER_STATE Store

        不做任何数据处理或图表渲染！
        """
        filters = {}

        # 处理文本输入筛选器（模糊搜索）
        if input_values:
            for i, val in enumerate(input_values):
                if val:  # 忽略空值
                    col_name = input_ids[i]['index']
                    filters[col_name] = {'value': val, 'method': 'fuzzy'}

        # 处理下拉筛选器（精确匹配）
        if dropdown_values:
            for i, val in enumerate(dropdown_values):
                if val:  # 忽略空值
                    col_name = dropdown_ids[i]['index']
                    filters[col_name] = {'value': val, 'method': 'exact'}

        # 使用StateManager创建标准格式的Store数据
        return StateManager.create_filter_state(filters=filters)

    # ---------------------------------------
    # 回调B: 收集图表配置 → 更新Store
    # ---------------------------------------
    @app.callback(
        Output(ComponentIDs.Store.CHART_CONFIG, 'data'),
        [Input(ComponentIDs.Visualizer.CHART_TYPE_DROPDOWN, 'value'),
         Input(ComponentIDs.Visualizer.X_AXIS_DROPDOWN, 'value'),
         Input(ComponentIDs.Visualizer.Y_AXIS_DROPDOWN, 'value'),
         Input(ComponentIDs.Visualizer.VIEW_SWITCHER, 'value'),
         Input(ComponentIDs.Visualizer.AGGREGATION_CHECKER, 'value')],
        prevent_initial_call=True
    )
    @ErrorHandler.handle_callback_error("图表配置更新", show_traceback=True)
    def update_chart_config(chart_type, x_axis, y_axis, view_opts, agg_opts):
        """
        收集图表配置并存入Store

        职责：
        - 收集图表类型、轴选择、视图选项
        - 打包成标准格式
        - 存入CHART_CONFIG Store

        不做任何图表渲染！
        """
        view_options = {
            'TRUNCATE': 'TRUNCATE' in (view_opts or []),
            'AGGREGATE': 'AGGREGATE' in (agg_opts or [])
        }

        # 使用StateManager创建标准格式
        return StateManager.create_chart_config(
            chart_type=chart_type or 'bar',
            x_axis=x_axis,
            y_axis=y_axis,
            view_options=view_options
        )

    # ---------------------------------------
    # 回调C: 监听Store → 渲染图表
    # ---------------------------------------
    @app.callback(
        Output(ComponentIDs.Visualizer.MAIN_GRAPH, 'figure'),
        [Input(ComponentIDs.Store.FILTER_STATE, 'data'),      # 监听筛选器Store
         Input(ComponentIDs.Store.CHART_CONFIG, 'data')],     # 监听图表配置Store
        prevent_initial_call=True
    )
    @ErrorHandler.safe_callback(default_return={'layout': {'title': '图表渲染失败'}})
    def render_chart(filter_state, chart_config):
        """
        纯渲染函数：从Store读取配置 → 生成图表

        职责：
        - 从FILTER_STATE Store读取筛选器配置
        - 从CHART_CONFIG Store读取图表配置
        - 从controller获取数据
        - 调用get_figure生成图表

        优势：
        - 只有2个参数！（vs 原来的9个）
        - 参数是Store数据，结构清晰
        - 添加新筛选器无需修改这个函数
        """
        # 获取数据
        df = controller.data
        if df is None or df.empty:
            return {'layout': {'title': '无可用数据，请先导入'}}

        # 从Store读取配置（而不是从9个参数！）
        filters = filter_state.get('filters', {}) if filter_state else {}

        if chart_config:
            view_options = chart_config.get('view_options', {})
            chart_type = chart_config.get('type', 'bar')
            x_axis = chart_config.get('x_axis')
            y_axis = chart_config.get('y_axis')
        else:
            # 默认值
            view_options = {'TRUNCATE': False, 'AGGREGATE': False}
            chart_type = 'bar'
            x_axis = None
            y_axis = None

        # 打包图表选项
        chart_options = {
            'type': chart_type,
            'x': x_axis,
            'y': y_axis
        }

        # 调用核心可视化引擎（保持不变）
        return get_figure(df, filters, view_options, chart_options)


# ===========================================
# 向后兼容性说明
# ===========================================
"""
这个重构版本保持了对外接口的兼容性：
1. create_visualizer_layout(df) - 签名不变
2. register_visualizer_callbacks(app, controller) - 签名不变
3. 使用相同的get_figure引擎

因此可以直接替换旧版本，无需修改其他模块。

如何切换：
1. 备份原文件：tab_visualizer.py → tab_visualizer_old.py
2. 重命名新文件：tab_visualizer_refactored.py → tab_visualizer.py
3. 在app.py中添加Store组件（见下一步）
4. 重启应用，测试功能
"""