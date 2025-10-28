import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import dash_bootstrap_components as dbc
from dash_bootstrap_components import Modal, ModalHeader, ModalBody, ModalFooter
import threading
import sys

# 导入我们的模块
from app.gui_app.gui_logger import create_log_report_table
from app.gui_app.tab_importer import create_importer_layout, register_importer_callbacks
from app.gui_app.tab_visualizer import create_visualizer_layout, register_visualizer_callbacks
from app.app_controller import AppController
from app.updater import check_for_updates
from app.utils import resource_path # 确保utils也被打包

# --- 版本号 ---
__version__ = "1.0.0"

# --- 1. 初始化Dash应用和控制器 ---
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
controller = AppController()

# --- 2. 定义应用的根布局 ---
app.layout = html.Div([
    html.H1(f'成本分析可视化工具 (V{__version__})'),
    dcc.Store(id='etl-status-store', storage_type='session'),
    dcc.Tabs(id="tabs-main", value='tab-visualizer', children=[
        dcc.Tab(label='数据导入与处理', value='tab-importer'),
        dcc.Tab(label='主分析与可视化', value='tab-visualizer'),
        dcc.Tab(label='已处理日志', value='tab-logger'),
    ]),
    html.Div(id='tabs-content'),
    Modal(
        id="drill-down-modal",
        size="xl",
        children=[
            ModalHeader(id="modal-header"),
            ModalBody(id="modal-body"),
            ModalFooter(dbc.Button("关闭", id="close-modal-button"))
        ]
    )
])

# --- 3. 注册所有模块的回调函数 ---
register_importer_callbacks(app, controller)
register_visualizer_callbacks(app, controller)

# --- 4. 编写“路由器”和“钻取”回调 ---
@app.callback(Output('tabs-content', 'children'),
              Input('tabs-main', 'value'))
def render_tab_content(tab):
    if tab == 'tab-importer':
        return create_importer_layout()
    elif tab == 'tab-visualizer':
        df = controller.get_latest_data()
        if df is None:
            df = pd.DataFrame() 
        return create_visualizer_layout(df)
    elif tab == 'tab-logger':
        return create_log_report_table()
    return html.H2("404 - 未找到页面")

@app.callback(
    [Output("drill-down-modal", "is_open"), Output("modal-header", "children"), Output("modal-body", "children")],
    [Input("main-interactive-graph", "clickData"), Input("close-modal-button", "n_clicks")],
    [State("drill-down-modal", "is_open")],
    prevent_initial_call=True
)
def display_click_data(clickData, close_clicks, is_open):
    ctx = dash.callback_context
    if (ctx.triggered and "close-modal-button" in ctx.triggered[0]["prop_id"]) or (is_open and clickData is None):
        return False, "", ""

    if clickData:
        if 'customdata' in clickData['points'][0] and isinstance(clickData['points'][0]['customdata'][0], list):
            indices = clickData['points'][0]['customdata'][0]
            df_full = controller.get_latest_data()
            if df_full is None or df_full.empty:
                return False, "错误", "无法加载数据进行钻取。"
            
            if not df_full.index.is_unique:
                df_full = df_full.reset_index(drop=True)

            drill_df = df_full.loc[indices]
            header = f"钻取明细 (共 {len(drill_df)} 项)"
            body = dash_table.DataTable(
                data=drill_df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in drill_df.columns],
                page_size=5,
                style_table={'overflowX': 'auto'}
            )
            return True, header, body
    return False, "", ""

# --- 5. 启动应用 ---
def run_update_check():
    """在一个单独的线程中运行更新检查。"""
    # 只有在打包后的EXE环境中才检查更新
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        update_thread = threading.Thread(target=check_for_updates, args=(__version__,))
        update_thread.daemon = True
        update_thread.start()

if __name__ == '__main__':
    run_update_check() # 检查更新
    print("启动Dash服务器...")
    app.run(debug=False) # 在生产环境中应关闭Debug模式
