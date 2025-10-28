import dash
from dash import dcc, html, Input, Output, State, dash_table
import base64
import os
import pandas as pd
import io

from app.utils import resource_path

# --- 路径定义 (可移植) ---
TEST_DATA_FILE = resource_path('data/raw/合肥in77项目筹开期合同及清单/1.精装修工程（一标二标）/合肥银泰in66项目精装修工程清单（地下-2层）一标段清单11.28-（调平版)-副本.xlsx')
TEMP_UPLOAD_DIR = resource_path('data/temp')

# --- 2. 模块化布局 (V49 - 可移植路径) ---
def create_importer_layout():
    """创建支持三阶段导入的布局，并确保目录存在。"""
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
        
    return html.Div([
        html.H3('步骤 1: 选择一个Excel文件'),
        dcc.Upload(
            id='upload-data',
            children=html.Div(['拖拽或 ', html.A('点击选择文件上传')]),
            style={
                'width': '90%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed',
                'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'
            }
        ),
        html.Button('使用默认文件进行测试', id='test-import-button', n_clicks=0, style={'margin': '10px'}),
        html.Hr(),
        
        dcc.Loading(
            id="loading-importer",
            type="circle",
            children=html.Div(id='importer-output-container')
        ),
    ])

# --- 3. 模块化回调 (V49 - 可移植路径) ---
def register_importer_callbacks(app, controller):
    """使用分离的回调来安全地处理三阶段导入流程。"""

    # 回调 A: 上传文件 -> 获取工作表列表
    @app.callback(
        Output('importer-output-container', 'children'),
        [Input('upload-data', 'contents'), 
         Input('test-import-button', 'n_clicks')],
        [State('upload-data', 'filename')],
        prevent_initial_call=True
    )
    def get_sheet_names(upload_contents, test_clicks, upload_filename):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        file_to_process = None
        original_filename = ''
        temp_file_path = None

        try:
            if trigger_id == 'upload-data' and upload_contents:
                content_type, content_string = upload_contents.split(',')
                decoded = base64.b64decode(content_string)
                temp_file_path = os.path.join(TEMP_UPLOAD_DIR, upload_filename)
                with open(temp_file_path, 'wb') as f:
                    f.write(decoded)
                file_to_process = temp_file_path
                original_filename = upload_filename

            elif trigger_id == 'test-import-button':
                file_to_process = TEST_DATA_FILE
                original_filename = os.path.basename(TEST_DATA_FILE)
            else:
                return dash.no_update

            sheet_names, message = controller.get_excel_sheet_names(file_to_process, original_filename)

            if not sheet_names:
                return html.Div(f"获取工作表失败: {message}", style={'color': 'red'})

            return html.Div([
                html.H3('步骤 2: 选择要解析的工作表'),
                dcc.Dropdown(
                    id='sheet-dropdown',
                    options=[{'label': name, 'value': name} for name in sheet_names],
                    placeholder="点击选择一个工作表..."
                ),
                html.Button('解析选中的工作表', id='parse-sheet-button', n_clicks=0, style={'marginTop': '10px'}),
                html.Div(id='importer-preview-container')
            ])

        except Exception as e:
            return html.Div(f"发生了一个意料之外的错误: {e}", style={'color': 'red'})
        finally:
            pass

    # 回调 B: 选择工作表 -> 解析并生成预览
    @app.callback(
        Output('importer-preview-container', 'children'),
        Input('parse-sheet-button', 'n_clicks'),
        State('sheet-dropdown', 'value'),
        prevent_initial_call=True
    )
    def stage_sheet_for_preview(n_clicks, selected_sheet):
        if n_clicks == 0 or not selected_sheet:
            return html.P("请先选择一个工作表再点击解析。", style={'color': 'orange'})

        df_preview, message = controller.parse_and_stage_excel(sheet_name=selected_sheet)

        if df_preview is None:
            return html.Div(f"文件解析失败: {message}", style={'color': 'red'})
        
        if df_preview.empty:
            return html.Div([
                html.H4("解析成功，但未发现有效数据行。", style={'color': 'orange'}),
                html.P("请检查工作表内容和表头是否符合规范。")
            ])

        buffer = io.StringIO()
        df_preview.info(buf=buffer)
        df_info_str = buffer.getvalue()

        return html.Div([
            html.H4("步骤 3: 预览数据并确认"),
            html.P(message),
            html.Details([
                html.Summary('点击展开/折叠 DataFrame 调试信息'),
                html.Pre(df_info_str, style={'backgroundColor': '#f0f0f0', 'padding': '10px', 'border': '1px solid #ddd'})
            ]),
            dash_table.DataTable(
                id='preview-table',
                data=df_preview.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df_preview.columns],
                page_size=10,
                style_table={'overflowX': 'auto'}
            ),
            html.Div([
                html.Button('确认并保存', id='commit-button', n_clicks=0, style={'margin': '10px', 'backgroundColor': '#28a745', 'color': 'white'}),
                html.Button('丢弃', id='discard-button', n_clicks=0, style={'margin': '10px'})
            ], style={'marginTop': '20px'})
        ])

    # 回调 C: 处理确认或丢弃操作
    @app.callback(
        Output('importer-output-container', 'children', allow_duplicate=True),
        [Input('commit-button', 'n_clicks'),
         Input('discard-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def commit_or_discard_staged_data(commit_clicks, discard_clicks):
        ctx = dash.callback_context
        if not ctx.triggered or (commit_clicks == 0 and discard_clicks == 0):
            return dash.no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'commit-button':
            success, message = controller.commit_staged_data()
            # 在提交成功后清理临时文件
            if success and controller.current_file_path and controller.current_file_path.startswith(TEMP_UPLOAD_DIR):
                try:
                    os.remove(controller.current_file_path)
                except OSError as e:
                    print(f"清理临时文件时出错 {controller.current_file_path}: {e}")
            
            if success:
                return html.Div(message, style={'color': 'green'})
            else:
                return html.Div(f"提交失败: {message}", style={'color': 'red'})
        
        elif trigger_id == 'discard-button':
            # 在丢弃后也清理临时文件
            temp_file_to_remove = controller.current_file_path
            controller.discard_staged_data()
            if temp_file_to_remove and temp_file_to_remove.startswith(TEMP_UPLOAD_DIR):
                try:
                    os.remove(temp_file_to_remove)
                except OSError as e:
                    print(f"清理临时文件时出错 {temp_file_to_remove}: {e}")
            return html.Div("操作已取消，暂存数据已丢弃。", style={'color': 'orange'})
        
        return dash.no_update
