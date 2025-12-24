"""
可视化模块 - 重构版（使用Store驱动架构）

重构目标：
1. 解决参数爆炸问题（从9个参数降到1-2个）
2. 使用Store作为中间层解耦Input和Output
3. 拆分成多个小回调，每个只做一件事
4. 使用ComponentIDs常量避免魔法字符串
5. 统一错误处理
6. 新增：展示筛选后的数据统计和明细表格
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
# --- 关键修改：导入 filter_dataframe ---
from app.analysis.visualizer import get_figure, filter_dataframe


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

    # --- V3 升级：动态生成筛选器 ---
    filters = []
    for col in all_columns:
        if df[col].dtype == 'object' or isinstance(df[col].dtype, pd.StringDtype):
            unique_values = df[col].unique()
            # 即使只有一个选项，也应该显示筛选器
            if 0 < len(unique_values) < 50:
                options = [{'label': str(i), 'value': i} for i in unique_values if i and pd.notna(i)]
                if not options: continue
                filters.append(
                    html.Div([
                        html.Label(col, className="form-label"),
                        dcc.Dropdown(
                            id=create_filter_id(col, 'dropdown'),
                            options=options,
                            className="form-select"
                        )
                    ], className="mb-3")
                )
            else:
                if '名称' in col:
                     filters.append(
                        html.Div([
                            html.Label(f'{col} (模糊搜索)', className="form-label"),
                            dcc.Input(
                                id=create_filter_id(col, 'input'),
                                type='text',
                                className="form-control"
                            )
                        ], className="mb-3")
                    )
    # --- 结束 V3 升级 ---

    view_switcher = dcc.Checklist(
        id=ComponentIDs.Visualizer.VIEW_SWITCHER,
        options=[{'label': '剔除长描述列', 'value': 'TRUNCATE'}],
        value=[],
        className="form-check"
    )

    agg_switcher = dcc.Checklist(
        id=ComponentIDs.Visualizer.AGGREGATION_CHECKER,
        options=[{'label': '合并同类项(仅条形图)', 'value': 'AGGREGATE'}],
        value=[],
        className="form-check"
    )

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
                    id=ComponentIDs.Visualizer.APPLY_FILTERS_BTN,
                    className="btn btn-primary w-100",
                    style={'marginTop': '15px'}
                )
            ], style={'width': '25%', 'padding': '10px', 'maxHeight': '90vh', 'overflowY': 'auto'}),

            # 右侧图表工作室
            html.Div([
                html.H3('图表工作室', className="mb-3"),
                html.Div([
                    dcc.Dropdown(
                        id=ComponentIDs.Visualizer.CHART_TYPE_DROPDOWN,
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
                        id=ComponentIDs.Visualizer.X_AXIS_DROPDOWN,
                        options=[{'label': i, 'value': i} for i in all_columns],
                        placeholder="选择X轴",
                        className="mb-2"
                    ),
                    dcc.Dropdown(
                        id=ComponentIDs.Visualizer.Y_AXIS_DROPDOWN,
                        options=[{'label': i, 'value': i} for i in numeric_columns],
                        placeholder="选择Y轴",
                        className="mb-2"
                    ),
                ]),
                dcc.Graph(
                    id=ComponentIDs.Visualizer.MAIN_GRAPH,
                    style={'height': '60vh'} # 稍微减小图表高度，为表格留出空间
                ),
                
                # --- 新增：数据统计和明细表格 ---
                html.Hr(),
                html.Div([
                    html.H4("筛选数据明细", className="mb-3"),
                    html.Div(id="filtered-data-stats", className="alert alert-info"), # 统计信息
                    dash_table.DataTable(
                        id="filtered-data-table",
                        columns=[{"name": i, "id": i} for i in df.columns],
                        data=[], # 初始为空，由回调填充
                        page_size=10,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'minWidth': '100px'},
                        style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'}
                    )
                ], className="mt-4")
                # --- 结束新增 ---
                
            ], style={'width': '75%', 'padding': '10px'})
        ], style={'display': 'flex'})
    ])


# ===========================================
# 2. 回调函数注册（Store驱动架构）
# ===========================================

def register_visualizer_callbacks(app, controller):
    """
    注册所有与可视化相关的回调
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
        filters = {}
        if input_values:
            for i, val in enumerate(input_values):
                if val:
                    col_name = input_ids[i]['index']
                    filters[col_name] = {'value': val, 'method': 'fuzzy'}
        if dropdown_values:
            for i, val in enumerate(dropdown_values):
                if val:
                    col_name = dropdown_ids[i]['index']
                    filters[col_name] = {'value': val, 'method': 'exact'}
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
        view_options = {
            'TRUNCATE': 'TRUNCATE' in (view_opts or []),
            'AGGREGATE': 'AGGREGATE' in (agg_opts or [])
        }
        return StateManager.create_chart_config(
            chart_type=chart_type or 'bar',
            x_axis=x_axis,
            y_axis=y_axis,
            view_options=view_options
        )

    # ---------------------------------------
    # 回调C: 监听Store → 渲染图表和表格 (已修复)
    # ---------------------------------------
    @app.callback(
        [Output(ComponentIDs.Visualizer.MAIN_GRAPH, 'figure'),
         Output("filtered-data-stats", "children"),  # 新增Output
         Output("filtered-data-table", "data")],     # 新增Output
        [Input(ComponentIDs.Store.FILTER_STATE, 'data'),
         Input(ComponentIDs.Store.CHART_CONFIG, 'data')],
        prevent_initial_call=True
    )
    @ErrorHandler.safe_callback(default_return=({'layout': {'title': '图表渲染失败'}}, "无数据", []))
    def render_chart_and_table(filter_state, chart_config):
        """
        更新图表、统计信息和数据表格
        """
        # 获取数据
        df = controller.data
        if df is None or df.empty:
            return {'layout': {'title': '无可用数据，请先导入'}}, "无可用数据", []

        # 从Store读取配置
        filters = filter_state.get('filters', {}) if filter_state else {}

        if chart_config:
            view_options = chart_config.get('view_options', {})
            chart_type = chart_config.get('type', 'bar')
            x_axis = chart_config.get('x_axis')
            y_axis = chart_config.get('y_axis')
        else:
            view_options = {'TRUNCATE': False, 'AGGREGATE': False}
            chart_type = 'bar'
            x_axis = None
            y_axis = None

        # --- 核心修复：先调用 filter_dataframe 获取筛选后的数据 ---
        # 1. 筛选数据
        dff = filter_dataframe(df, filters, view_options)
        
        # 2. 生成统计信息
        row_count = len(dff)
        stats_text = f"当前筛选条件下共有 {row_count} 行数据。"

        # 3. 生成表格数据 (只展示前1000行以保证性能)
        table_data = dff.head(1000).to_dict('records')

        # 4. 生成图表 (传入 filtered_df=dff，避免重复筛选)
        chart_options = {'type': chart_type, 'x': x_axis, 'y': y_axis}
        fig = get_figure(df, filters, view_options, chart_options, filtered_df=dff)

        return fig, stats_text, table_data
