import pandas as pd
import os
import json
from dash import html, dash_table

# 定义元数据索引文件的路径
PROCESSED_DATA_DIR = 'F:/cost_analyzer/data/processed/'
INDEX_FILE = os.path.join(PROCESSED_DATA_DIR, 'index.json')

def create_log_report_table():
    """
    读取元数据索引文件，并创建一个可交互的Dash DataTable组件。
    :return: 一个Dash DataTable组件，或一个提示信息。
    """
    if not os.path.exists(INDEX_FILE):
        return html.Div("暂无已处理的文件历史记录。")

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    # 将JSON数据转换为DataTable期望的格式 (list of dicts)
    data_for_table = [
        {
            '文件名 (机器可读)': key,
            '原始文件名 (中文)': value.get('original_filename', ''),
            '项目名 (中文)': value.get('project_name_cn', ''),
            '处理时间': value.get('processed_at', '')
        }
        for key, value in index_data.items()
    ]

    # 创建并返回DataTable组件
    log_table = dash_table.DataTable(
        id='log-table',
        columns=[
            {"name": "文件名 (机器可读)", "id": "文件名 (机器可读)"},
            {"name": "原始文件名 (中文)", "id": "原始文件名 (中文)"},
            {"name": "项目名 (中文)", "id": "项目名 (中文)"},
            {"name": "处理时间", "id": "处理时间"},
        ],
        data=data_for_table,
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        sort_action="native", # 启用原生排序
        page_size=10, # 每页显示10条记录
    )

    return log_table
