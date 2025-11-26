"""
成本分析可视化工具 - 主应用入口（重构版）

版本: 2.0.0 (重构版)
重构日期: 2024-11-25

重构内容：
1. ✅ Store驱动架构 - 使用dcc.Store管理应用状态
2. ✅ 组件ID管理 - 使用ComponentIDs常量避免魔法字符串
3. ✅ 统一错误处理 - ErrorHandler统一消息展示
4. ✅ 回调模块化 - 拆分大回调为多个小回调
5. ✅ 解决Output冲突 - 每个Output只有一个回调

对比旧版本：
- 参数数量：9个 → 1-2个
- 回调冲突：是（allow_duplicate） → 否
- 状态管理：Python对象 → dcc.Store（可持久化）
- 错误处理：不统一 → 统一
- 组件ID：魔法字符串 → 常量

使用方法：
1. 备份原app.py → app_old.py
2. 重命名本文件 app.py → app.py
3. 运行 python app.py
4. 访问 http://127.0.0.1:8050
"""

import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import dash_bootstrap_components as dbc
from dash_bootstrap_components import Modal, ModalHeader, ModalBody, ModalFooter
import threading
import sys

# 导入新的基础设施
from app.component_ids import ComponentIDs
from app.state_manager import create_all_stores
from app.utils.error_handler import ErrorHandler

# 导入重构后的GUI模块
from app.gui_app.gui_logger import create_log_report_table
from app.gui_app.tab_importer_refactored import create_importer_layout, register_importer_callbacks
from app.gui_app.tab_visualizer_refactored import create_visualizer_layout, register_visualizer_callbacks

# 导入控制器和工具
from app.app_controller import AppController
from app.updater import check_for_updates
from app.utils.resource_path import resource_path  # 使用新的导入路径

# --- 版本号 ---
__version__ = "2.0.0"  # 重构版本号

# ===========================================
# 1. 初始化Dash应用和控制器
# ===========================================

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]  # 使用Bootstrap主题
)

controller = AppController()

# ===========================================
# 2. 定义应用的根布局（集成Store）
# ===========================================

app.layout = html.Div([
    # 应用标题
    html.H1(
        f'成本分析可视化工具 (V{__version__})',
        className="text-center my-4"
    ),

    # *** 关键改进：添加所有Store组件 ***
    *create_all_stores(),  # 一次性创建所有Store

    # 主选项卡
    dcc.Tabs(
        id=ComponentIDs.TABS_MAIN,  # 使用常量
        value='tab-visualizer',
        children=[
            dcc.Tab(label='数据导入与处理', value='tab-importer'),
            dcc.Tab(label='主分析与可视化', value='tab-visualizer'),
            dcc.Tab(label='已处理日志', value='tab-logger'),
        ],
        className="nav-tabs"
    ),

    # 内容区域
    html.Div(id=ComponentIDs.TABS_CONTENT, className="container-fluid"),  # 使用常量

    # 数据钻取模态框
    Modal(
        id=ComponentIDs.Modal.DRILL_DOWN,  # 使用常量
        size="xl",
        children=[
            ModalHeader(id=ComponentIDs.Modal.HEADER),  # 使用常量
            ModalBody(id=ComponentIDs.Modal.BODY),  # 使用常量
            ModalFooter(
                dbc.Button(
                    "关闭",
                    id=ComponentIDs.Modal.CLOSE_BTN,  # 使用常量
                    className="btn-secondary"
                )
            )
        ]
    )
], className="container-fluid")

# ===========================================
# 3. 注册所有模块的回调函数
# ===========================================

# 注册导入模块的回调（重构版）
register_importer_callbacks(app, controller)

# 注册可视化模块的回调（重构版）
register_visualizer_callbacks(app, controller)

# ===========================================
# 4. 主应用回调（路由和钻取）
# ===========================================

@app.callback(
    Output(ComponentIDs.TABS_CONTENT, 'children'),  # 使用常量
    Input(ComponentIDs.TABS_MAIN, 'value')  # 使用常量
)
@ErrorHandler.handle_callback_error("选项卡切换")
def render_tab_content(tab):
    """
    根据选中的选项卡渲染内容

    职责：
    - 路由不同的选项卡内容
    - 加载必要的数据

    参数：
        tab: 选中的选项卡值

    返回：
        对应的布局组件
    """
    if tab == 'tab-importer':
        return create_importer_layout()

    elif tab == 'tab-visualizer':
        # 加载最新数据
        df = controller.get_latest_data()
        if df is None:
            df = pd.DataFrame()
        return create_visualizer_layout(df)

    elif tab == 'tab-logger':
        return create_log_report_table()

    else:
        return html.H2("404 - 未找到页面", className="text-center text-danger")


@app.callback(
    [Output(ComponentIDs.Modal.DRILL_DOWN, 'is_open'),  # 使用常量
     Output(ComponentIDs.Modal.HEADER, 'children'),  # 使用常量
     Output(ComponentIDs.Modal.BODY, 'children')],  # 使用常量
    [Input(ComponentIDs.Visualizer.MAIN_GRAPH, 'clickData'),  # 使用常量
     Input(ComponentIDs.Modal.CLOSE_BTN, 'n_clicks')],  # 使用常量
    [State(ComponentIDs.Modal.DRILL_DOWN, 'is_open')],  # 使用常量
    prevent_initial_call=True
)
@ErrorHandler.safe_callback(default_return=(False, "", ""))
def display_click_data(clickData, close_clicks, is_open):
    """
    处理图表点击事件，显示数据钻取模态框

    职责：
    - 处理图表点击事件
    - 提取钻取数据
    - 显示模态框

    参数：
        clickData: 点击数据
        close_clicks: 关闭按钮点击次数
        is_open: 模态框是否打开

    返回：
        (是否打开模态框, 标题, 内容)
    """
    ctx = dash.callback_context

    # 处理关闭按钮
    if ctx.triggered and ComponentIDs.Modal.CLOSE_BTN in ctx.triggered[0]["prop_id"]:
        return False, "", ""

    # 处理图表点击
    if clickData:
        # 检查是否有自定义数据（包含钻取索引）
        if 'customdata' in clickData['points'][0] and \
           isinstance(clickData['points'][0]['customdata'][0], list):

            indices = clickData['points'][0]['customdata'][0]
            df_full = controller.get_latest_data()

            if df_full is None or df_full.empty:
                return True, "错误", html.P("无法加载数据进行钻取。")

            # 确保索引唯一性
            if not df_full.index.is_unique:
                df_full = df_full.reset_index(drop=True)

            # 提取钻取数据
            drill_df = df_full.loc[indices]

            # 创建标题和内容
            header = f"钻取明细 (共 {len(drill_df)} 项)"
            body = dash_table.DataTable(
                data=drill_df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in drill_df.columns],
                page_size=5,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                }
            )

            return True, header, body

    return False, "", ""


# ===========================================
# 5. 启动应用
# ===========================================

def run_update_check():
    """
    在单独的线程中运行更新检查

    只在打包后的EXE环境中执行更新检查。
    """
    # 只有在打包后的EXE环境中才检查更新
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        update_thread = threading.Thread(
            target=check_for_updates,
            args=(__version__,)
        )
        update_thread.daemon = True
        update_thread.start()


if __name__ == '__main__':
    # 启动更新检查
    run_update_check()

    # 启动Dash服务器
    print("=" * 60)
    print(f"成本分析可视化工具 V{__version__} (重构版)")
    print("=" * 60)
    print("启动Dash服务器...")
    print("访问地址: http://127.0.0.1:8050")
    print("\n重构改进:")
    print("  ✅ Store驱动架构 - 状态管理更清晰")
    print("  ✅ 组件ID管理 - 消除魔法字符串")
    print("  ✅ 回调模块化 - 从9个参数降到1-2个")
    print("  ✅ 解决Output冲突 - 消除allow_duplicate")
    print("  ✅ 统一错误处理 - 用户体验更好")
    print("=" * 60)
    print()

    # 在生产环境中应关闭Debug模式
    # 重构版建议先用debug=True测试，确保无误后再关闭
    app.run(debug=True, host='127.0.0.1', port=8050)


# ===========================================
# 向后兼容性说明
# ===========================================
"""
这个重构版本的主要变化：

1. 新增模块：
   - app/component_ids.py - 组件ID常量管理
   - app/state_manager.py - Store状态管理
   - app/utils/error_handler.py - 错误处理
   - app/utils/resource_path.py - 资源路径工具

2. 重构模块：
   - app/gui_app/tab_visualizer_refactored.py - 可视化模块（9个参数→2个）
   - app/gui_app/tab_importer_refactored.py - 导入模块（消除Output冲突）

3. 保持不变：
   - app/app_controller.py - 控制器
   - app/analysis/excel_parser.py - Excel解析器
   - app/analysis/visualizer.py - 可视化引擎
   - app/gui_app/gui_logger.py - 日志查看器
   - app/updater.py - 更新检测器

4. 迁移路径：
   步骤1: 先用app_refactored.py测试，确保功能正常
   步骤2: 备份原app.py → app_old.py
   步骤3: 重命名app_refactored.py → app.py
   步骤4: 同样重命名tab_*_refactored.py → tab_*.py

5. 回滚方法：
   如果出现问题，直接恢复app_old.py即可

6. 测试清单：
   □ 文件上传功能
   □ 工作表选择和解析
   □ 数据预览和提交
   □ 图表筛选功能
   □ 图表类型切换
   □ 数据钻取功能
   □ 历史记录查看
   □ 页面刷新后状态保持（新功能）
"""