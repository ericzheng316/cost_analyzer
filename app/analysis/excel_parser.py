"""
Excel智能解析器 (V5.1 - 调试增强版)

核心功能：
1. 语义识别表头。
2. 模块化流水线：列识别 -> 行分类 -> 结构构建 -> 类型清洗。
3. 智能列名识别：通过语义找到"序号"列，而非硬编码。
4. 规则增强：中文序号("一","二")直接判定为L2层级。
5. 兜底机制：确保前端筛选器始终可见。
6. 调试输出：控制台打印层级结构摘要。
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
import re

# --- 导入 ---
try:
    from sentence_transformers import SentenceTransformer, util
    from sklearn.metrics.pairwise import cosine_similarity
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
# --- 结束导入 ---


# ===========================================
# 语义行分类器 (V5)
# ===========================================
class SemanticRowClassifier:
    """
    提供语义分析能力：
    1. 识别表头行。
    2. 识别列名（找到哪一列是'序号'）。
    3. 识别行层级（L1/L2/L3）。
    """
    def __init__(self):
        self.model = None
        self.level_embeddings = {}
        if not SENTENCE_TRANSFORMER_AVAILABLE:
            print("警告: 未安装sentence-transformers库，语义分析功能将不可用。")
            return
            
        try:
            model_id = "BAAI/bge-small-zh-v1.5"
            print(f"正在加载语义模型: {model_id}...")
            self.model = SentenceTransformer(model_id)
            print("✅ 语义模型加载成功。")
            
            # 1. 表头原型
            self.HEADER_PROTOTYPES = [
                "序号", "功能区", "项目名称", "施工内容及主要做法", "计算规则", 
                "供应方式或分包说明", "计量单位", "工程量", "不含税综合单价", 
                "不含税合价", "主材单价", "损耗率", "人工费", "备注"
            ]
            self.header_embedding = self.model.encode(self.HEADER_PROTOTYPES, normalize_embeddings=True)

            # 2. 层级概念原型
            level_prototypes = {
                1: "1F 2F 3F 4F B1 B2 B3 一楼 二楼 地下室 裙楼 主楼 围挡工程 拆除工程 室外部分 建筑总览", 
                2: "大厅 中庭 公区 走廊 后场 卫生间 电梯厅 办公室 楼梯间 核心筒 强电 弱电 给排水", 
                3: "地面 墙面 天花 顶面 柜体 门窗 踢脚线 固定装置 细节" 
            }
            for level, doc in level_prototypes.items():
                self.level_embeddings[level] = self.model.encode(doc, normalize_embeddings=True)

            # 3. 关键列名原型 (用于查找列)
            self.col_prototypes = {
                'serial': self.model.encode("序号 编号 No. 序列 ID", normalize_embeddings=True),
                'project': self.model.encode("项目名称 工程名称 施工项目 Item Name", normalize_embeddings=True)
            }

        except Exception as e:
            print(f"❌ 语义模型加载失败: {e}")
            self.model = None

    def find_header_row(self, df: pd.DataFrame, max_rows_to_scan: int = 20) -> int:
        """查找最佳表头行"""
        if not self.model: return -1
        candidate_scores = []
        for i, row in df.head(max_rows_to_scan).iterrows():
            row_texts = [str(cell).strip() for cell in row.dropna().tolist() if str(cell).strip()]
            if len(row_texts) < 3: continue
            candidate_embeddings = self.model.encode(row_texts, normalize_embeddings=True)
            sim_matrix = cosine_similarity(candidate_embeddings, self.header_embedding)
            row_score = np.mean(sim_matrix.max(axis=1)) * (len(row_texts) / len(self.HEADER_PROTOTYPES))
            candidate_scores.append({'row_index': i, 'score': row_score})
        
        if not candidate_scores: return -1
        best = max(candidate_scores, key=lambda x: x['score'])
        return best['row_index'] if best['score'] > 0.3 else -1

    def find_best_column_match(self, columns: List[str], target_type: str) -> Optional[str]:
        """
        在给定的列名列表中，找到与 target_type ('serial' 或 'project') 语义最接近的列名。
        """
        if not self.model or not columns: return None
        
        # 编码所有列名
        col_embeddings = self.model.encode(columns, normalize_embeddings=True)
        target_embedding = self.col_prototypes.get(target_type)
        
        if target_embedding is None: return None

        # 计算相似度
        similarities = util.cos_sim(col_embeddings, target_embedding).flatten()
        
        best_idx = int(similarities.argmax())
        best_score = float(similarities[best_idx])
        
        # 阈值判断，防止匹配到完全无关的列
        if best_score > 0.4:
            return columns[best_idx]
        return None

    def classify_hierarchy_level(self, row_texts: List[str]) -> int:
        """语义判断行层级"""
        if not self.model or not row_texts: return 0
        full_text = ". ".join(row_texts)
        row_embedding = self.model.encode(full_text, normalize_embeddings=True)
        similarities = {lvl: util.cos_sim(row_embedding, emb).item() for lvl, emb in self.level_embeddings.items()}
        if not similarities: return 0
        best_level = max(similarities, key=similarities.get)
        return best_level if similarities[best_level] > 0.35 else 0


# ===========================================
# 子功能模块 (流水线步骤)
# ===========================================

def _identify_critical_columns(df: pd.DataFrame, classifier: SemanticRowClassifier) -> Tuple[Optional[str], Optional[str]]:
    """
    步骤 1: 智能识别关键列名 (序号列, 项目名称列)
    """
    columns = [str(c) for c in df.columns]
    
    # 1. 尝试使用语义模型查找
    serial_col = classifier.find_best_column_match(columns, 'serial')
    project_col = classifier.find_best_column_match(columns, 'project')
    
    # 2. 兜底：如果模型没找到，尝试简单的关键词匹配
    if not serial_col:
        serial_col = next((c for c in columns if '序号' in c or '编号' in c), None)
    if not project_col:
        project_col = next((c for c in columns if '名称' in c or '项目' in c), None)
        
    print(f"列识别结果: 序号列='{serial_col}', 项目列='{project_col}'")
    return serial_col, project_col


def _classify_rows_strategy(df: pd.DataFrame, serial_col: Optional[str], project_col: Optional[str], classifier: SemanticRowClassifier) -> List[Dict]:
    """
    步骤 2: 行角色分类策略
    """
    row_tags = []
    chinese_numeral_pattern = re.compile(r'^[一二三四五六七八九十百]+$')
    
    for index, row in df.iterrows():
        tag = {'type': 'UNKNOWN', 'level': 0, 'text': ''}
        
        # 获取序号列内容
        serial_val = str(row[serial_col]).strip() if serial_col and pd.notna(row[serial_col]) else ""
        
        # --- 策略 A: 中文数字 -> L2 ---
        if serial_col and chinese_numeral_pattern.match(serial_val):
            tag['type'] = 'HIERARCHY'
            tag['level'] = 2
            # 提取文本：优先项目列，否则取第一个非空文本
            if project_col and pd.notna(row[project_col]):
                tag['text'] = str(row[project_col]).strip()
            else:
                texts = [str(c).strip() for c in row.dropna() if str(c).strip()]
                tag['text'] = texts[0] if texts else "未命名L2"
                
        # --- 策略 B: 阿拉伯数字 -> DATA ---
        elif serial_col and pd.to_numeric(row[serial_col], errors='coerce') is not np.nan:
            tag['type'] = 'DATA'
            
        # --- 策略 C: 语义模型兜底 ---
        else:
            row_texts = [str(cell).strip() for cell in row.dropna().tolist() if str(cell).strip()]
            if row_texts:
                level = classifier.classify_hierarchy_level(row_texts)
                if level > 0:
                    tag['type'] = 'HIERARCHY'
                    tag['level'] = level
                    if project_col and pd.notna(row[project_col]):
                        tag['text'] = str(row[project_col]).strip()
                    else:
                        tag['text'] = row_texts[0]
        
        row_tags.append(tag)
    return row_tags


def _build_hierarchy_structure(df: pd.DataFrame, row_tags: List[Dict]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    步骤 3: 根据行标签构建树形结构
    """
    structured_metadata = {}
    
    # 确定最大层级
    max_level = max((t['level'] for t in row_tags), default=0)
    max_level = max(max_level, 2) # 至少有L2
    
    # 初始化层级列
    for i in range(1, max_level + 1):
        df[f'功能区_L{i}'] = np.nan
        
    current_path = {i: None for i in range(1, max_level + 1)}
    
    for i in range(len(df)):
        tag = row_tags[i]
        
        if tag['type'] == 'DATA':
            # 数据行：继承当前路径
            for level, value in current_path.items():
                df.loc[i, f'功能区_L{level}'] = value
                
        elif tag['type'] == 'HIERARCHY':
            # 层级行：更新路径
            lvl = tag['level']
            current_path[lvl] = tag['text']
            # 清空更深层级
            for l in range(lvl + 1, max_level + 1):
                current_path[l] = None
            # 自身也填充路径
            for l, value in current_path.items():
                df.loc[i, f'功能区_L{l}'] = value
                
    return df, structured_metadata


def _finalize_data_types(df: pd.DataFrame, serial_col: Optional[str]) -> pd.DataFrame:
    """
    步骤 4: 数据清洗、类型转换与兜底
    """
    # 1. 序号列转数字
    if serial_col:
        df[serial_col] = pd.to_numeric(df[serial_col], errors='coerce')
        
    # 2. 智能类型推断
    for col in df.columns:
        if col == serial_col: continue
        
        # 兜底：层级列填充"未分类"，确保前端可见
        if col.startswith('功能区_L'):
            df[col] = df[col].fillna('未分类')
            continue
            
        # 采样判断是否为数字列
        sample = df[col].dropna().head(50)
        if sample.empty:
            df[col] = df[col].fillna('').astype(str)
            continue
            
        numeric_count = pd.to_numeric(sample, errors='coerce').notna().sum()
        if numeric_count / len(sample) > 0.8:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = df[col].fillna('').astype(str)
            
    return df

# --- 新增：调试打印函数 ---
def _print_hierarchy_summary(df: pd.DataFrame):
    """
    在控制台打印层级结构的摘要信息，用于调试。
    """
    print("\n" + "="*40)
    print("📊 层级结构解析摘要")
    print("="*40)
    
    # 打印 L1
    if '功能区_L1' in df.columns:
        l1_items = df['功能区_L1'].unique().tolist()
        print(f"\n[L1 层级] (共 {len(l1_items)} 个):")
        print(l1_items)
        
        # 打印 L2 (按 L1 分组)
        if '功能区_L2' in df.columns:
            print(f"\n[L2 层级] (按 L1 分组):")
            for l1 in l1_items:
                l2_items = df[df['功能区_L1'] == l1]['功能区_L2'].unique().tolist()
                # 过滤掉 '未分类' 如果它不是唯一的
                l2_items = [x for x in l2_items if x != '未分类' or len(l2_items) == 1]
                if l2_items:
                    print(f"  └─ {l1}: {l2_items}")
                    
                    # 打印 L3 (按 L2 分组)
                    if '功能区_L3' in df.columns:
                        for l2 in l2_items:
                            l3_items = df[(df['功能区_L1'] == l1) & (df['功能区_L2'] == l2)]['功能区_L3'].unique().tolist()
                            l3_items = [x for x in l3_items if x != '未分类' or len(l3_items) == 1]
                            if l3_items:
                                print(f"      └─ {l2}: {l3_items}")

    print("="*40 + "\n")
# -------------------------


def _clean_and_structure_data(df: pd.DataFrame, classifier: SemanticRowClassifier) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    主编排函数：串联所有步骤
    """
    # 0. 基础清理
    df.dropna(how='all', inplace=True)
    if df.empty: return df, {}
    df.reset_index(drop=True, inplace=True) # 关键：对齐索引
    
    # 1. 识别关键列
    serial_col, project_col = _identify_critical_columns(df, classifier)
    
    # 2. 行分类
    row_tags = _classify_rows_strategy(df, serial_col, project_col, classifier)
    
    # 3. 构建结构
    df, metadata = _build_hierarchy_structure(df, row_tags)
    
    # 4. 最终清洗
    df = _finalize_data_types(df, serial_col)
    
    # 5. 调试打印
    _print_hierarchy_summary(df)
    
    return df, metadata


# ===========================================
# 主解析函数 (入口)
# ===========================================
def intelligent_read_excel(file_path: str, sheet_name: Optional[str | int] = None) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    智能读取Excel文件，自动识别表头、提取元数据并返回清理后的DataFrame。
    """
    metadata = {"source_sheet": sheet_name}
    
    # --- 阶段0: 初始化 ---
    classifier = SemanticRowClassifier()
    if not classifier.model:
        metadata["error"] = "语义模型加载失败。"
        return None, metadata

    try:
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    except Exception as e:
        metadata["error"] = f"读取Excel文件失败: {e}"
        return None, metadata

    # --- 阶段1: 表头查找 ---
    header_row_index = classifier.find_header_row(df_raw)
    if header_row_index == -1:
        metadata["error"] = "无法自动定位表头。"
        return None, metadata
    metadata['header_row'] = header_row_index

    # --- 阶段2: 创建初始DataFrame ---
    header_block = df_raw.iloc[header_row_index:header_row_index + 3]
    
    # 合并表头
    temp_columns = []
    last_valid_col = ''
    for i, col_name in enumerate(header_block.iloc[0]):
        if pd.notna(col_name) and str(col_name).strip():
            last_valid_col = str(col_name).strip().replace('\n', '')
        sub_col_names = [str(header_block.iloc[j][i]).strip().replace('\n', '') 
                         for j in range(1, len(header_block)) if pd.notna(header_block.iloc[j][i])]
        full_col_name = ' '.join([last_valid_col] + sub_col_names)
        temp_columns.append(full_col_name.strip())

    # 提取公式/代码 (保持不变)
    relations = {'formulas': {}, 'codes': {}}
    for _, row in header_block.iterrows():
        if row.str.contains(r'^[A-Z]\s*=', na=False).any():
            for i, cell in enumerate(row):
                if isinstance(cell, str) and re.match(r'^[A-Z]\s*=', cell):
                    relations['formulas'][temp_columns[i]] = cell
        elif row.str.match(r'^[a-z]$', na=False).any():
            for i, cell in enumerate(row):
                if isinstance(cell, str) and re.match(r'^[a-z]$', cell):
                    relations['codes'][cell] = temp_columns[i]
    metadata['relations'] = relations

    # 处理重复列名
    final_columns = []
    counts = {}
    for col in temp_columns:
        counts[col] = counts.get(col, 0) + 1
        if counts[col] > 1:
            final_columns.append(f"{col}_{counts[col]-1}")
        else:
            final_columns.append(col)

    df_initial = df_raw.iloc[header_row_index + len(header_block):].copy()
    df_initial.columns = final_columns
    metadata['columns_found'] = df_initial.columns.tolist()

    # --- 阶段3: 模块化清洗与结构化 ---
    df_final, structured_metadata = _clean_and_structure_data(df_initial, classifier)
    metadata.update(structured_metadata)
    
    return df_final, metadata
