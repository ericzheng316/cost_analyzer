import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

# 将项目根目录添加到sys.path，以确保可以正确导入app模块
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from app.analysis import process_excel_file
except ImportError as e:
    messagebox.showerror("导入错误", f"无法导入处理模块: {e}\n请确保 app/analysis.py 文件存在。")
    sys.exit(1)

def select_file_and_process():
    """
    打开一个文件对话框来选择Excel文件，然后调用处理函数。
    """
    # 为文件对话框定义接受的文件类型
    file_types = [
        ('Excel files', '*.xlsx *.xls'),
        ('All files', '*.*')
    ]

    # 设定默认打开的目录为项目下的 data/raw
    initial_dir = os.path.join(project_root, 'data', 'raw')
    if not os.path.isdir(initial_dir):
        initial_dir = project_root # 如果目录不存在，则使用项目根目录

    # 打开文件选择对话框
    file_path = filedialog.askopenfilename(
        title='请选择一个Excel成本文件',
        initialdir=initial_dir,
        filetypes=file_types
    )

    if file_path:
        # 更新标签以显示所选文件的路径
        file_path_label.config(text=f"已选择文件: {file_path}")
        print(f"GUI: 已选择文件: {file_path}")
        
        # 调用 analysis 模块中的处理函数
        dataframe = process_excel_file(file_path)
        
        if dataframe is not None:
            messagebox.showinfo("成功", f"文件 '{os.path.basename(file_path)}' 已成功处理！\n\n读取到 {len(dataframe)} 行数据。")
        else:
            messagebox.showerror("失败", f"处理文件 '{os.path.basename(file_path)}' 时发生错误。\n请查看控制台输出获取更多信息。")
    else:
        # 如果用户取消了选择
        file_path_label.config(text="未选择文件")
        print("GUI: 用户取消了文件选择。")

# --- GUI 界面设置 ---
# 创建主窗口
root = tk.Tk()
root.title("成本分析器")
root.geometry("700x250") # 设置窗口大小

# 创建一个主框架以更好地组织控件
main_frame = tk.Frame(root, padx=15, pady=15)
main_frame.pack(expand=True, fill=tk.BOTH)

# 创建一个按钮，点击后触发文件选择和处理函数
select_button = tk.Button(
    main_frame,
    text="选择要分析的Excel文件",
    command=select_file_and_process,
    font=("Arial", 12),
    pady=10
)
select_button.pack(pady=20)

# 创建一个标签，用于显示所选文件的路径
file_path_label = tk.Label(main_frame, text="尚未选择文件", wraplength=650, justify=tk.LEFT)
file_path_label.pack(pady=10)

# 启动GUI事件循环
root.mainloop()
