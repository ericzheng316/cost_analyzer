import os
import json
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List
import pandas as pd
import io

from app.analysis.excel_parser import intelligent_read_excel
from app.utils import resource_path

# --- 路径定义 (可移植) ---
# 使用 resource_path 来获取在任何环境下都正确的路径
PROCESSED_DATA_DIR = resource_path('data/processed')
INDEX_FILE = os.path.join(PROCESSED_DATA_DIR, 'index.json')

# --- 确保目录存在 ---
# 在应用启动时，检查并创建必要的目录
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

class AppController:
    """
    Acts as a mediator between the GUI and the business logic.
    Manages application state, including staged data for preview.
    """
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None # Currently active data for visualization
        self.staged_data: Optional[pd.DataFrame] = None # Data waiting for commit
        self.staged_metadata: Optional[Dict[str, Any]] = None # Metadata for staged data
        self.current_file_path: Optional[str] = None # Path of the file currently being processed
        self.current_original_filename: Optional[str] = None # Original filename of the file currently being processed

    def load_index(self) -> dict:
        """Loads the metadata index file."""
        if not os.path.exists(INDEX_FILE):
            return {}
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save_index(self, index: dict) -> None:
        """Saves the metadata index file."""
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=4)

    def get_excel_sheet_names(self, file_path: str, original_filename: str) -> Tuple[List[str], str]:
        """
        Reads an Excel file and returns a list of sheet names.
        Stores the file path and original filename for later use.
        """
        self.current_file_path = file_path
        self.current_original_filename = original_filename
        try:
            excel_file = pd.ExcelFile(file_path)
            return excel_file.sheet_names, "成功获取工作表名称。"
        except Exception as e:
            print(f"[控制器错误] 获取工作表名称时发生异常: {e}")
            return [], f"获取工作表名称失败: {e}"

    def parse_and_stage_excel(self, sheet_name: Optional[str | int] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Parses the currently stored Excel file and stages it for preview.
        """
        if not self.current_file_path:
            return None, "没有文件路径可供解析，请先上传文件。"

        try:
            df, metadata = intelligent_read_excel(self.current_file_path, sheet_name=sheet_name)
            
            if df is None:
                error_message = metadata.get("error", "未知的解析错误")
                return None, f"解析失败: {error_message}"
            
            self.staged_data = df
            self.staged_metadata = metadata
            self.staged_metadata['original_filename'] = self.current_original_filename 

            print("数据已成功解析并暂存以供预览。")
            return self.staged_data, "解析成功，请预览下方数据。"

        except Exception as e:
            print(f"[控制器错误] 暂存过程中发生异常: {e}")
            return None, f"处理过程中发生意外错误: {e}"

    def commit_staged_data(self) -> Tuple[bool, str]:
        """
        Commits the staged data to the processed directory.
        """
        if self.staged_data is None or self.staged_metadata is None:
            return False, "没有暂存的数据可供提交。"

        try:
            df = self.staged_data
            original_filename = self.staged_metadata.get('original_filename', 'unknown_file')

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_key = f"{timestamp}_{original_filename.rsplit('.', 1)[0]}.parquet"
            processed_path = os.path.join(PROCESSED_DATA_DIR, file_key)
            df.to_parquet(processed_path)

            index = self.load_index()
            index[file_key] = {
                "original_filename": original_filename,
                "processed_timestamp": timestamp,
                "project_name": "合肥银杏项目", # Placeholder
                "source_sheet": self.staged_metadata.get("source_sheet", "N/A"),
                "total_rows": len(df),
                "total_columns": len(df.columns)
            }
            self.save_index(index)

            self.data = df
            self.discard_staged_data()
            
            return True, f"文件 '{original_filename}' 已成功保存。"

        except Exception as e:
            print(f"[控制器错误] 提交数据时发生异常: {e}")
            return False, f"提交数据时发生错误: {e}"

    def discard_staged_data(self) -> None:
        """Clears any staged data and resets file paths."""
        self.staged_data = None
        self.staged_metadata = None
        self.current_file_path = None
        self.current_original_filename = None
        print("暂存数据已被丢弃。")

    def get_latest_data(self) -> Optional[pd.DataFrame]:
        """
        Loads and returns the most recently processed data frame.
        """
        index = self.load_index()
        if not index:
            return None
        try:
            latest_file_key = max(index.keys())
            self.data = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, latest_file_key))
            return self.data
        except (ValueError, FileNotFoundError):
            return None
