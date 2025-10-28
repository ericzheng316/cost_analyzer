import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import numpy as np

# 导入统一的可视化引擎
from app.analysis.visualizer import get_figure

# --- 1. 模块化布局 --- 
def create_visualizer_layout(df):
    """根据提供的数据帧创建可视化选项卡的布局。"""
    if df is None or df.empty:
        return html.Div("无可用数据，请先在“数据导入与处理”选项卡中导入数据。")

    all_columns = df.columns.tolist()
    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()

    # 根据数据动态生成筛选器
    filters = []
    for col in all_columns:
        if col == '项目名称':
            filters.append(html.Div([html.Label(f'{col} (模糊搜索)'), dcc.Input(id={'type': 'filter-input', 'index': col}, type='text')]))
        elif df[col].dtype == 'object' and 1 < df[col].nunique() < 50:
            options = [{'label': i, 'value': i} for i in df[col].unique() if i]
            filters.append(html.Div([html.Label(col), dcc.Dropdown(id={'type': 'filter-dropdown', 'index': col}, options=options)]))
    
    view_switcher = dcc.Checklist(id='view-switcher-checklist', options=[{'label': '剔除长描述列', 'value': 'TRUNCATE'}], value=[])
    agg_switcher = dcc.Checklist(id='aggregation-checklist', options=[{'label': '合并同类项(仅条形图)', 'value': 'AGGREGATE'}], value=[])

    return html.Div([
        html.Div([
            html.Div([
                html.H3('高级筛选器'), 
                *filters, 
                view_switcher, 
                agg_switcher, 
                html.Button('应用并更新图表', id='apply-filters-button', style={'marginTop': '15px'})
            ], style={'width': '25%', 'padding': '10px'}),
            html.Div([
                html.H3('图表工作室'),
                dcc.Dropdown(id='chart-type-dropdown', options=[
                    {'label': '条形图', 'value': 'bar'}, {'label': '饼图', 'value': 'pie'}, {'label': '散点图', 'value': 'scatter'},
                    {'label': '折线图', 'value': 'line'}, {'label': '直方图', 'value': 'histogram'}, {'label': '箱形图', 'value': 'box'}
                ], value='bar'),
                dcc.Dropdown(id='x-axis-dropdown', options=[{'label': i, 'value': i} for i in all_columns], placeholder="选择X轴"),
                dcc.Dropdown(id='y-axis-dropdown', options=[{'label': i, 'value': i} for i in numeric_columns], placeholder="选择Y轴"),
                dcc.Graph(id='main-interactive-graph', style={'height': '80vh'})
            ], style={'width': '75%', 'padding': '10px'})
        ], style={'display': 'flex'})
    ])

# --- 2. 使用Controller的回调 --- 
def register_visualizer_callbacks(app, controller):
    """注册所有与可视化相关的回调，并使用controller获取数据。"""
    @app.callback(
        Output('main-interactive-graph', 'figure'),
        Input('apply-filters-button', 'n_clicks'),
        [State({'type': 'filter-input', 'index': dash.ALL}, 'value'),
         State({'type': 'filter-dropdown', 'index': dash.ALL}, 'value'),
         State({'type': 'filter-input', 'index': dash.ALL}, 'id'),
         State({'type': 'filter-dropdown', 'index': dash.ALL}, 'id'),
         State('view-switcher-checklist', 'value'),
         State('aggregation-checklist', 'value'),
         State('chart-type-dropdown', 'value'),
         State('x-axis-dropdown', 'value'),
         State('y-axis-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_main_graph(n_clicks, input_values, dropdown_values, input_ids, dropdown_ids, view_options_val, agg_options_val, chart_type, x_axis, y_axis):
        # 从控制器获取当前的数据状态
        df = controller.data
        if df is None or df.empty:
            return {'layout': {'title': '无可用数据，请先导入'}}

        # 1. 打包所有筛选器
        filters = {}
        if input_values:
            for i, val in enumerate(input_values):
                if val: filters[input_ids[i]['index']] = {'value': val, 'method': 'fuzzy'}
        if dropdown_values:
            for i, val in enumerate(dropdown_values):
                if val: filters[dropdown_ids[i]['index']] = {'value': val, 'method': 'exact'}

        # 2. 打包所有视图选项
        view_options = {
            'TRUNCATE': 'TRUNCATE' in view_options_val,
            'AGGREGATE': 'AGGREGATE' in agg_options_val
        }

        # 3. 打包所有图表选项
        chart_options = {'type': chart_type, 'x': x_axis, 'y': y_axis}

        # 4. 将所有打包好的信息传递给核心引擎
        return get_figure(df, filters, view_options, chart_options)
