"""
Excel智能解析器 V2.1 (逻辑解耦版)

设计理念：
1. 职责分离：本模块只负责解析，不再负责任何文件IO操作。
2. 数据返回：将解析出的 DataFrame 和 JSON Tree 作为结果返回给调用者（Controller）。
3. 模块化流水线：保持内部的策略选择、行分类、树构建的清晰结构。
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
import re
import json
import os
from datetime import datetime

# --- 导入语义模型 (可选增强) ---
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False

# ===========================================
# 1. 基础工具类与常量
# ===========================================

class ParsingStrategy:
    ORDINAL = "ORDINAL"   # 序号层级型 (一、二、...)
    KEYWORD = "KEYWORD"   # 关键词层级型 (1F, B1...)
    UNKNOWN = "UNKNOWN"

class RowType:
    HEADER = "HEADER"
    L1_NODE = "L1"
    L2_NODE = "L2"
    ITEM = "ITEM"
    UNKNOWN = "UNKNOWN"

# ===========================================
# 2. 阶段一：全局模式识别 (StructureDetector)
# ===========================================

class StructureDetector:
    """
    负责扫描文件前部，决定解析策略。
    """
    def __init__(self):
        self.chinese_numeral_pattern = re.compile(r'^[一二三四五六七八九十]+[、\.]?')
        self.floor_keyword_pattern = re.compile(r'(?i)(\d+F|B\d+|地下|屋顶|一层|二层)')

    def detect_strategy(self, df: pd.DataFrame, header_row_index: int) -> str:
        """
        扫描数据区域（表头之后），判定策略。
        """
        sample_df = df.iloc[header_row_index+1 : header_row_index+51]
        
        serial_col_idx = -1
        for i, col in enumerate(df.iloc[header_row_index]):
            if pd.notna(col) and ("序号" in str(col) or "编号" in str(col)):
                serial_col_idx = i
                break
        
        ordinal_score = 0
        keyword_score = 0
        
        for _, row in sample_df.iterrows():
            if serial_col_idx != -1 and serial_col_idx < len(row):
                val = str(row.iloc[serial_col_idx]).strip()
                if self.chinese_numeral_pattern.match(val):
                    ordinal_score += 1
            
            non_empty_count = row.count()
            row_text = " ".join([str(x) for x in row.dropna()])
            if non_empty_count < 5 and self.floor_keyword_pattern.search(row_text):
                keyword_score += 1

        print(f"[策略检测] Ordinal Score: {ordinal_score}, Keyword Score: {keyword_score}")
        
        if ordinal_score > 0:
            return ParsingStrategy.ORDINAL
        elif keyword_score > 0:
            return ParsingStrategy.KEYWORD
        else:
            return ParsingStrategy.KEYWORD

# ===========================================
# 3. 阶段二：行级分类决策树 (RowClassifier)
# ===========================================

class RowClassifier:
    """
    根据选定的策略，对每一行进行分类。
    """
    def __init__(self, strategy: str, columns: List[str]):
        self.strategy = strategy
        self.columns = columns
        
        self.chinese_numeral = re.compile(r'^[一二三四五六七八九十]+[、\.]?')
        self.floor_pattern = re.compile(r'(?i)^(\d+F|B\d+|地下|屋顶|一层|二层|三层|首层)')
        self.area_pattern = re.compile(r'(?i)(公共|公区|卫生间|电梯|走廊|大厅|中庭|后场|系统)')
        
        self.serial_col = next((c for c in columns if '序号' in str(c)), None)
        self.price_col = next((c for c in columns if '单价' in str(c) and '综合' in str(c)), None)
        self.unit_col = next((c for c in columns if '单位' in str(c)), None)
        self.name_col = next((c for c in columns if '名称' in str(c) or '项目' in str(c)), None)

    def classify_row(self, row: pd.Series) -> Dict[str, Any]:
        """
        输入一行数据，返回分类结果。
        """
        if row.dropna().empty:
            return {'type': RowType.UNKNOWN}
            
        is_item = False
        
        serial_val = str(row[self.serial_col]).strip() if self.serial_col and pd.notna(row[self.serial_col]) else ""
        if serial_val.isdigit() or re.match(r'^\d+(\.\d+)?$', serial_val):
            is_item = True
            
        price_val = row[self.price_col] if self.price_col else None
        unit_val = row[self.unit_col] if self.unit_col else None
        
        has_price = pd.to_numeric(price_val, errors='coerce') > 0 if pd.notna(price_val) else False
        has_unit = pd.notna(unit_val) and str(unit_val).strip() != ""
        
        if has_price and has_unit:
            is_item = True
            
        if is_item:
            return {'type': RowType.ITEM, 'name': str(row[self.name_col]) if self.name_col else "未命名项"}

        row_text = str(row[self.name_col]).strip() if self.name_col and pd.notna(row[self.name_col]) else ""
        if not row_text:
            texts = [str(x).strip() for x in row.dropna()]
            row_text = texts[0] if texts else ""

        if self.strategy == ParsingStrategy.ORDINAL:
            if self.chinese_numeral.match(serial_val) or self.chinese_numeral.match(row_text):
                return {'type': RowType.L1_NODE, 'name': row_text}
            return {'type': RowType.L2_NODE, 'name': row_text}

        elif self.strategy == ParsingStrategy.KEYWORD:
            if self.floor_pattern.search(row_text):
                return {'type': RowType.L1_NODE, 'name': row_text}
            elif self.area_pattern.search(row_text):
                return {'type': RowType.L2_NODE, 'name': row_text}
            else:
                return {'type': RowType.L2_NODE, 'name': row_text}
                
        return {'type': RowType.UNKNOWN}

# ===========================================
# 4. 阶段三：树构建逻辑 (TreeBuilder)
# ===========================================

class TreeBuilder:
    """
    基于栈的树形结构构建器。
    """
    def __init__(self, project_name: str):
        self.root = {
            "project_name": project_name,
            "children": []
        }
        self.stack = [self.root]
        self.flat_rows = []

    def process_row(self, row_data: pd.Series, classification: Dict[str, Any]):
        """
        处理一行已分类的数据，更新树和扁平化列表。
        """
        node_type = classification['type']
        node_name = classification.get('name', '未命名')
        
        if node_type == RowType.UNKNOWN:
            return

        if node_type == RowType.L1_NODE:
            while len(self.stack) > 1:
                self.stack.pop()
            new_node = {"type": "L1", "name": node_name, "children": []}
            self.stack[-1]["children"].append(new_node)
            self.stack.append(new_node)
            
        elif node_type == RowType.L2_NODE:
            if len(self.stack) > 0 and self.stack[-1].get("type") == "L2":
                self.stack.pop()
            if len(self.stack) == 1:
                virtual_l1 = {"type": "L1", "name": "未分类区域", "children": []}
                self.stack[-1]["children"].append(virtual_l1)
                self.stack.append(virtual_l1)
            new_node = {"type": "L2", "name": node_name, "children": []}
            self.stack[-1]["children"].append(new_node)
            self.stack.append(new_node)
            
        elif node_type == RowType.ITEM:
            if len(self.stack) == 1:
                virtual_l1 = {"type": "L1", "name": "未分类区域", "children": []}
                self.stack[-1]["children"].append(virtual_l1)
                self.stack.append(virtual_l1)
            if self.stack[-1].get("type") == "L1":
                virtual_l2 = {"type": "L2", "name": "通用项目", "children": []}
                self.stack[-1]["children"].append(virtual_l2)
                self.stack.append(virtual_l2)
            
            item_data = {k: v for k, v in row_data.to_dict().items() if pd.notna(v)}
            item_node = {"type": "ITEM", "name": node_name, "data": item_data}
            self.stack[-1]["children"].append(item_node)
            
            l1_name = next((n['name'] for n in self.stack if n.get('type') == 'L1'), None)
            l2_name = next((n['name'] for n in self.stack if n.get('type') == 'L2'), None)
            
            flat_row = row_data.copy()
            flat_row['功能区_L1'] = l1_name
            flat_row['功能区_L2'] = l2_name
            self.flat_rows.append(flat_row)

    def get_json_tree(self) -> Dict:
        return self.root
        
    def get_flat_dataframe(self) -> pd.DataFrame:
        if not self.flat_rows:
            return pd.DataFrame()
        return pd.DataFrame(self.flat_rows)

# ===========================================
# 5. 主入口函数 (兼容旧接口)
# ===========================================

def intelligent_read_excel(file_path: str, sheet_name: Optional[str | int] = None) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    智能读取Excel文件 (V2 架构)。
    """
    metadata = {"source_sheet": sheet_name}
    
    try:
        # 1. 读取原始数据
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        # 2. 定位表头
        header_row_index = -1
        max_score = 0
        for i, row in df_raw.head(20).iterrows():
            score = sum(1 for x in row.dropna() if str(x) in ['序号', '项目名称', '单价', '合价', '单位'])
            if score > max_score:
                max_score = score
                header_row_index = i
        
        if header_row_index == -1:
            metadata["error"] = "无法定位表头"
            return None, metadata
            
        metadata['header_row'] = header_row_index
        
        # 3. 处理表头和列名
        columns = [str(x).strip() if pd.notna(x) else f"Unnamed_{i}" for i, x in enumerate(df_raw.iloc[header_row_index])]
        
        df_data = df_raw.iloc[header_row_index+1:].copy()
        df_data.columns = columns
        df_data.reset_index(drop=True, inplace=True)
        
        # 4. 阶段一：策略检测
        detector = StructureDetector()
        strategy = detector.detect_strategy(df_raw, header_row_index)
        print(f"🔍 检测到的解析策略: {strategy}")
        
        # 5. 阶段二 & 三：逐行分类与构建
        classifier = RowClassifier(strategy, columns)
        builder = TreeBuilder(project_name=os.path.basename(file_path))
        
        for _, row in df_data.iterrows():
            classification = classifier.classify_row(row)
            builder.process_row(row, classification)
            
        # 6. 获取结果
        df_final = builder.get_flat_dataframe()
        json_tree = builder.get_json_tree()
        
        # --- 核心修改：不再保存文件，而是将JSON树放入元数据中返回 ---
        metadata['json_tree'] = json_tree
        
        # 7. 最终类型清洗
        for col in df_final.columns:
            if '单价' in col or '合价' in col or '工程量' in col or '序号' in col:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
        
        metadata['columns_found'] = df_final.columns.tolist()
        if '功能区_L1' in df_final.columns: metadata['l1_column'] = '功能区_L1'
        if '功能区_L2' in df_final.columns: metadata['l2_column'] = '功能区_L2'
        
        return df_final, metadata

    except Exception as e:
        metadata["error"] = f"解析过程发生异常: {e}"
        import traceback
        traceback.print_exc()
        return None, metadata
