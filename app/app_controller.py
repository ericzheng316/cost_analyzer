import os
import json
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List
import pandas as pd
import io
import shutil

# --- 关键修改：使用新的解析器 ---
from app.analysis.excel_parser_v2 import intelligent_read_excel
from app.utils.resource_path import resource_path

# --- 路径定义 (可移植) ---
# 使用 resource_path 来获取在任何环境下都正确的路径
PROCESSED_DATA_DIR = resource_path('data/processed')
AUTOSAVE_DIR = resource_path('data/autosave') # 新增：暂存目录
DATABASE_DIR = resource_path('data/database') # 新增：最终归档目录
INDEX_FILE = os.path.join(PROCESSED_DATA_DIR, 'index.json')

# --- 确保目录存在 ---
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(AUTOSAVE_DIR, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

class AppController:
    """
    Acts as a mediator between the GUI and the business logic.
    Manages application state, including staged data for preview.
    """
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.staged_data: Optional[pd.DataFrame] = None
        self.staged_metadata: Optional[Dict[str, Any]] = None
        self.current_file_path: Optional[str] = None
        self.current_original_filename: Optional[str] = None

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
        Parses the Excel file, stages it for preview, and autosaves the JSON tree.
        """
        if not self.current_file_path:
            return None, "没有文件路径可供解析，请先上传文件。"

        try:
            # --- 关键修改：确保使用 V2 解析器 ---
            df, metadata = intelligent_read_excel(self.current_file_path, sheet_name=sheet_name)
            
            if df is None:
                error_message = metadata.get("error", "未知的解析错误")
                return None, f"解析失败: {error_message}"
            
            self.staged_data = df
            self.staged_metadata = metadata
            self.staged_metadata['original_filename'] = self.current_original_filename 

            # --- 新增：自动保存 JSON 树到暂存区 ---
            json_tree = self.staged_metadata.get('json_tree')
            if json_tree:
                autosave_path = self._get_autosave_json_path()
                try:
                    with open(autosave_path, 'w', encoding='utf-8') as f:
                        json.dump(json_tree, f, ensure_ascii=False, indent=2)
                    print(f"✅ JSON 树已自动暂存至: {autosave_path}")
                except Exception as e:
                    print(f"⚠️ 暂存 JSON 失败: {e}")
            # ------------------------------------

            print("数据已成功解析并暂存以供预览。")
            return self.staged_data, "解析成功，请预览下方数据。"

        except Exception as e:
            print(f"[控制器错误] 暂存过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
            return None, f"处理过程中发生意外错误: {e}"

    def commit_staged_data(self) -> Tuple[bool, str]:
        """
        Commits the staged data: saves Parquet and moves JSON tree to database.
        """
        if self.staged_data is None or self.staged_metadata is None:
            return False, "没有暂存的数据可供提交。"

        try:
            df = self.staged_data
            original_filename = self.staged_metadata.get('original_filename', 'unknown_file')

            # 1. 保存 Parquet 文件 (保持不变)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_key = f"{timestamp}_{original_filename.rsplit('.', 1)[0]}.parquet"
            processed_path = os.path.join(PROCESSED_DATA_DIR, file_key)
            df.to_parquet(processed_path)

            # 2. 更新索引 (保持不变)
            index = self.load_index()
            index[file_key] = {
                "original_filename": original_filename,
                "processed_timestamp": timestamp,
                "project_name": "合肥银杏项目", # Placeholder
                "source_sheet": self.staged_metadata.get("source_sheet", "N/A"),
                "total_rows": len(df),
                "total_columns": len(df.columns)
            }
            
            # --- 新增：移动 JSON 树到最终归档目录 ---
            autosave_path = self._get_autosave_json_path()
            if autosave_path and os.path.exists(autosave_path):
                db_path = self._get_database_json_path(timestamp, original_filename)
                shutil.move(autosave_path, db_path)
                index[file_key]['json_tree_path'] = db_path # 在索引中记录最终路径
                print(f"✅ JSON 树已归档至: {db_path}")
            # -----------------------------------------
            
            self.save_index(index)

            self.data = df
            self.discard_staged_data(cleanup_files=False) # 提交成功后只清理内存，不删文件
            
            return True, f"文件 '{original_filename}' 已成功保存。"

        except Exception as e:
            print(f"[控制器错误] 提交数据时发生异常: {e}")
            return False, f"提交数据时发生错误: {e}"

    def discard_staged_data(self, cleanup_files: bool = True) -> None:
        """
        Clears any staged data and optionally cleans up autosaved files.
        """
        # --- 新增：清理暂存的 JSON 文件 ---
        if cleanup_files:
            autosave_path = self._get_autosave_json_path()
            if autosave_path and os.path.exists(autosave_path):
                try:
                    os.remove(autosave_path)
                    print(f"🗑️ 已清理暂存的 JSON 文件: {autosave_path}")
                except OSError as e:
                    print(f"⚠️ 清理暂存文件失败: {e}")
        # ---------------------------------

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

    # --- 新增：辅助函数，用于生成文件名 ---
    def _get_autosave_json_path(self) -> Optional[str]:
        """Gets the path for the autosaved JSON tree file."""
        if not self.current_original_filename:
            return None
        filename = f"{os.path.splitext(self.current_original_filename)[0]}_tree.json"
        return os.path.join(AUTOSAVE_DIR, filename)

    def _get_database_json_path(self, timestamp: str, original_filename: str) -> Optional[str]:
        """Gets the path for the final database JSON tree file."""
        if not original_filename:
            return None
        # 命名与 Parquet 文件保持一致，便于关联
        filename = f"{timestamp}_{os.path.splitext(original_filename)[0]}_tree.json"
        return os.path.join(DATABASE_DIR, filename)
    # ------------------------------------
