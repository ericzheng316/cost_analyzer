import pandas as pd
import plotly.express as px
from thefuzz import fuzz

# --- 搜索模块 (稳定) ---
def advanced_search(df: pd.DataFrame, search_criteria: dict):
    results = df.copy()
    for column, criteria in search_criteria.items():
        if column not in results.columns: 
            print(f"警告: 列 '{column}' 不存在，跳过此筛选条件。")
            continue
        value = criteria.get('value')
        method = criteria.get('method', 'exact')
        if method == 'exact': 
            results = results[results[column] == value]
        elif method == 'fuzzy':
            threshold = criteria.get('threshold', 70)
            # Ensure the column is of string type for fuzzy search
            scores = results[column].astype(str).apply(lambda x: fuzz.partial_ratio(value, x))
            results = results[scores >= threshold]
    return results

# --- 绘图模块 (修正) ---
def _plot_chart(df: pd.DataFrame, chart_type: str, x_axis: str, y_axis: str, title: str, custom_data_cols: list):
    plot_functions = {
        'bar': px.bar, 'scatter': px.scatter, 'line': px.line, 
        'box': px.box, 'pie': px.pie, 'histogram': px.histogram
    }
    plot_func = plot_functions.get(chart_type, px.bar)

    # The custom_data needs to be a list of columns from the dataframe
    # Ensure the columns exist in the dataframe being plotted
    valid_custom_data_cols = [col for col in custom_data_cols if col in df.columns]

    kwargs = {
        'data_frame': df,
        'title': title,
        'custom_data': valid_custom_data_cols
    }
    if chart_type in ['bar', 'scatter', 'line', 'box']:
        kwargs.update({'x': x_axis, 'y': y_axis})
    elif chart_type == 'pie':
        kwargs.update({'names': x_axis, 'values': y_axis})
    elif chart_type == 'histogram':
        kwargs.update({'x': x_axis})

    fig = plot_func(**kwargs)
    
    # Update hovertemplate to use the valid custom data columns
    fig.update_traces(hovertemplate="<br>".join([f"<b>{col}</b>: %{{customdata[{i}]}}" for i, col in enumerate(valid_custom_data_cols)]))
    fig.update_layout(hoverlabel=dict(align="left"))
    return fig

# --- 统一数据处理与可视化引擎 (修正) ---
def get_figure(df: pd.DataFrame, filters: dict, view_options: dict, chart_options: dict):
    """
    接收所有UI输入，完成数据处理和可视化的完整流程。
    """
    if df.empty: 
        return px.bar(title="无可用数据，请先导入")

    # 1. 从chart_options中尽早提取变量
    chart_type = chart_options.get('type')
    x_axis = chart_options.get('x')
    y_axis = chart_options.get('y')

    # 2. 关键检查
    if not all([chart_type, x_axis]): 
        return px.bar(title="请选择图表类型和X轴")
    if chart_type not in ['histogram'] and not y_axis:
        # Pie charts also need a value, but we handle that implicitly
        return px.bar(title="请为该图表类型选择Y轴")

    dff = df.copy()

    # 3. 应用筛选
    if filters:
        dff = advanced_search(dff, filters)

    # 4. 应用视图切换（剔除长描述）
    if view_options.get('TRUNCATE'):
        long_text_columns = ['施工内容及主要做法', '计算规则', '供应方式或分包说明']
        cols_to_drop = [col for col in long_text_columns if col in dff.columns]
        dff = dff.drop(columns=cols_to_drop)

    # 5. 定义标题和自定义数据
    title = f'{y_axis} vs. {x_axis}' if y_axis else f'Distribution of {x_axis}'
    custom_data_cols = dff.columns.tolist()
    plot_df = dff

    # 6. 应用聚合逻辑
    if view_options.get('AGGREGATE') and chart_type == 'bar' and y_axis:
        # Add original index for drill-down before grouping
        dff_agg = dff.reset_index()
        agg_logic = {
            y_axis: pd.NamedAgg(column=y_axis, aggfunc='mean'),
            'index': pd.NamedAgg(column='index', aggfunc=list)
        }
        plot_df = dff_agg.groupby(x_axis).agg(**agg_logic).reset_index()
        # The custom data for aggregated plots should be the index list
        plot_df = plot_df.rename(columns={'index': 'drill_down_indices'})
        custom_data_cols = ['drill_down_indices']
        title += " (均值)"
    
    # 7. 调用绘图函数
    return _plot_chart(plot_df, chart_type, x_axis, y_axis, title, custom_data_cols)
