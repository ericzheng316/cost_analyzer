import pandas as pd
import numpy as np
# 导入我们所有的模块
from excel_parser import intelligent_read_excel
from visualizer import (
    advanced_search, 
    plot_bar_chart_interactive, # 导入新的交互式函数
    handle_plot_interactive   # 导入新的交互式处理器
)

def process_and_visualize(file_path: str, sheet_name: str | int = 0):
    """
    完整的处理流程：读取、高级搜索、并生成可交互的图表。
    """
    print(f"--- 开始完整处理流程 ---")
    
    # 1. 智能读取
    result = intelligent_read_excel(file_path, sheet_name=sheet_name)
    if not result: print("读取失败，流程终止。"); return
    df, metadata = result
    print("\n--- 智能读取成功 ---")

    # 2. 定义搜索条件并执行
    search_criteria = {"功能区_L2": {"value": "地面", "method": "exact"}}
    print(f"\n--- 开始高级搜索 ---\n搜索条件: {search_criteria}")
    filtered_df = advanced_search(df, search_criteria)
    if filtered_df.empty: print("未找到满足所有条件的项目。"); return
    print(f"找到 {len(filtered_df)} 个匹配项目。")

    # --- 演示新的交互式引擎 --- #
    price_col = '不含税综合单价(元)'
    filtered_df[price_col] = pd.to_numeric(filtered_df[price_col], errors='coerce')
    filtered_df.dropna(subset=[price_col], inplace=True)

    # 1. 定义我们希望在悬停时看到的额外信息
    hover_info = ['功能区_L1', '不含税合价(元)', '工程量']

    # 2. 创建一个可交互的图表对象
    fig = plot_bar_chart_interactive(
        df=filtered_df, 
        x_col='项目名称', 
        y_col=price_col, 
        title='地面-各类项目单价对比 (可交互)',
        hover_data=hover_info
    )

    # 3. 演示“即时预览”：直接在浏览器中打开
    print("\n--- 1. 演示即时预览 ---")
    handle_plot_interactive(fig)

    # 4. 演示“保存交互式文件”
    print("\n--- 2. 演示保存交互式HTML文件 ---")
    output_file = "F:/cost_analyzer/output/interactive_report.html"
    handle_plot_interactive(fig, output_path=output_file)

if __name__ == '__main__':
    test_file = 'F:/cost_analyzer/data/raw/合肥in77项目筹开期合同及清单/1.精装修工程（一标二标）/合肥银泰in66项目精装修工程清单（地下-2层）一标段清单11.28-（调平版)-副本.xlsx'
    target_sheet = '【01】装饰工程(地下-2层）'

    if test_file:
        process_and_visualize(test_file, sheet_name=target_sheet)
