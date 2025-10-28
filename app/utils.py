import sys
import os

def resource_path(relative_path: str) -> str:
    """
    获取资源的绝对路径，无论是作为脚本运行还是作为PyInstaller打包后的EXE运行。
    
    Args:
        relative_path: 相对于项目根目录的路径 (例如 'data/raw/test.xlsx')

    Returns:
        一个在任何环境下都有效的绝对路径。
    """
    try:
        # PyInstaller 会创建一个临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        # 如果不在PyInstaller打包环境中，则获取项目根目录
        # 此文件位于 app/utils.py, 因此根目录是上一级目录
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)
