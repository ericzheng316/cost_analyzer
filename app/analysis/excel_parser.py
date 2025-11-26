"""
Excel智能解析器

核心功能：
1. 智能识别多行、合并单元格的表头
2. 自动提取列中的计算公式
3. 自动提取单字母代码与列名的对应关系
4. 自动识别并填充分层结构（L1/L2）
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any, List

# --- 新增导入 ---
try:
    from sentence_transformers import SentenceTransformer, util
    from sklearn.metrics.pairwise import cosine_similarity
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
# --- 结束新增导入 ---


# ===========================================
# 语义表头查找器 (新功能)
# ===========================================
class HeaderFinder:
    """
    使用sentence-transformer模型通过语义相似度查找表头。
    """
    def __init__(self):
        self.model = None
        self.golden_embeddings = None
        if SENTENCE_TRANSFORMER_AVAILABLE:
            try:
                # 模型ID
                model_id = "BAAI/bge-small-zh-v1.5"
                print(f"正在加载语义模型: {model_id}...")
                # 加载模型
                self.model = SentenceTransformer(model_id)
                print("✅ 语义模型加载成功。")
                
                # 定义最理想的“黄金标准”表头
                self.GOLDEN_HEADERS = [
                    "序号", "功能区", "项目名称", "施工内容及主要做法", "计算规则", 
                    "供应方式或分包说明", "计量单位", "工程量", "不含税综合单价", 
                    "不含税合价", "主材单价", "损耗率", "主材单价(含损耗)", 
                    "人工费", "辅材费", "机械费", "管理费率、利润率", "备注"
                ]
                # 对黄金标准进行编码，只做一次
                self.golden_embeddings = self.model.encode(self.GOLDEN_HEADERS, normalize_embeddings=True)

            except Exception as e:
                print(f"❌ 语义模型加载失败: {e}")
                print("将回退到基于规则的算法。")
                self.model = None
        else:
            print("未安装sentence-transformers库，将使用基于规则的算法。")

    def find_header_row_semantic(self, df: pd.DataFrame, max_rows_to_scan: int = 20) -> int:
        """
        通过计算与黄金标准的语义相似度来查找最佳表头行。

        返回:
            最佳表头行的索引，如果找不到则返回-1。
        """
        if not self.model:
            return -1 # 表示模型不可用

        candidate_scores = []

        for i, row in df.head(max_rows_to_scan).iterrows():
            # 清理行数据，只保留非空、有意义的文本
            row_texts = [str(cell).strip() for cell in row.dropna().tolist() if str(cell).strip()]
            
            # 忽略太稀疏或看起来不像表头的行
            if len(row_texts) < 3:
                continue

            # 编码候选行
            candidate_embeddings = self.model.encode(row_texts, normalize_embeddings=True)
            
            # 计算相似度矩阵
            sim_matrix = cosine_similarity(candidate_embeddings, self.golden_embeddings)
            
            # 为每个候选单元格找到其在黄金标准中的最高相似度得分
            best_matches_scores = sim_matrix.max(axis=1)
            
            # 行的总分是所有单元格最佳匹配得分的平均值
            # 乘以一个权重，该权重考虑了匹配到的黄金表头数量，以惩罚匹配不全的行
            row_score = np.mean(best_matches_scores) * (len(row_texts) / len(self.GOLDEN_HEADERS))
            
            candidate_scores.append({'row_index': i, 'score': row_score})

        if not candidate_scores:
            return -1

        # 找到得分最高的候选行
        best_candidate = max(candidate_scores, key=lambda x: x['score'])
        
        # 设置一个置信度阈值，低于此阈值则认为没有找到合适的表头
        confidence_threshold = 0.3
        if best_candidate['score'] < confidence_threshold:
            print(f"警告: 语义分析找到的最佳表头候选行得分较低 ({best_candidate['score']:.2f})，可能不准确。")
            return -1

        print(f"语义分析找到的最佳表头行: {best_candidate['row_index']} (得分: {best_candidate['score']:.2f})")
        return best_candidate['row_index']


# ===========================================
# 基于规则的表头查找器 (备用方案)
# ===========================================
def get_row_score(row: pd.Series) -> float:
    """
    为一行计算“表头相似度”得分（基于规则）。
    """
    score = 0
    num_non_empty = 0
    
    # 核心关键词和它们的权重
    keywords = {
        '项目': 3, '名称': 3, '单价': 3, '合价': 3, '工程量': 3, '单位': 2,
        '序号': 2, '功能区': 1, '内容': 1, '规则': 1, '方式': 1, '备注': 1
    }

    for item in row:
        if pd.notna(item):
            num_non_empty += 1
            s_item = str(item)
            # 关键词匹配得分
            for keyword, weight in keywords.items():
                if keyword in s_item:
                    score += weight
            # 字符串类型得分
            if isinstance(item, str):
                score += 0.5
            # 惩罚长文本
            if len(s_item) > 50:
                score -= 10
    
    # 惩罚只有一个单元格的行
    if num_non_empty <= 1:
        return 0
        
    # 根据非空单元格的比例进行归一化
    return score / num_non_empty if num_non_empty > 0 else 0

def find_header_row_rule_based(df: pd.DataFrame, max_rows_to_scan: int = 20) -> int:
    """
    通过评分系统找到最可能是表头的行。
    """
    scores = [get_row_score(df.iloc[i]) for i in range(min(len(df), max_rows_to_scan))]
    if not scores:
        return -1
        
    best_row_index = np.argmax(scores)
    
    # 检查得分是否高于某个阈值
    if scores[best_row_index] < 2.0: # 这是一个经验阈值
        return -1

    print(f"规则分析找到的最佳表头行: {best_row_index} (得分: {scores[best_row_index]:.2f})")
    return int(best_row_index)


# ===========================================
# 数据清洗与结构化 (优化版)
# ===========================================
def _clean_and_structure_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    对解析后的数据进行清洗、结构化和类型转换。
    此版本会保留摘要行，以提供上下文，但会清空其序号。
    """
    structured_metadata = {}

    # 1. 移除完全为空的行
    df.dropna(how='all', inplace=True)
    if df.empty:
        return df, structured_metadata

    # 2. 识别有效数据行 vs 摘要行
    # 一个可靠的标志是'序号'列是否可以被转换为数字
    serial_col = next((col for col in df.columns if '序号' in col), None)
    if not serial_col:
        # 如果没有序号列，我们假设所有行都是数据行
        df['is_data_row'] = True
    else:
        # 尝试将序号列转为数字，无法转换的为NaN
        numeric_serial = pd.to_numeric(df[serial_col], errors='coerce')
        # 数据行是那些序号为数字的行
        df['is_data_row'] = numeric_serial.notna()

    # 3. 创建L1/L2分层结构
    # 使用非数据行（摘要行）来创建L1结构
    l1_col, l2_col = None, None
    # 查找'功能区'列并重命名为L2
    potential_l2_col = next((col for col in df.columns if '功能区' in col), None)
    if potential_l2_col:
        df.rename(columns={potential_l2_col: '功能区_L2'}, inplace=True)
        l2_col = '功能区_L2'
        structured_metadata['l2_column'] = l2_col
    
    # 查找'项目名称'列以提取L1信息
    project_name_col = next((col for col in df.columns if '项目名称' in col), None)
    if project_name_col:
        # L1的值来自于非数据行的'项目名称'列
        df['功能区_L1'] = np.where(~df['is_data_row'], df[project_name_col], np.nan)
        # 向下填充L1值到所有后续行
        df['功能区_L1'].fillna(method='ffill', inplace=True)
        l1_col = '功能区_L1'
        structured_metadata['l1_column'] = l1_col

    # 4. 清理摘要行的序号，但不删除行
    # 这是关键步骤，满足用户“保留摘要行但清空序号”的需求
    if serial_col:
        df[serial_col] = pd.to_numeric(df[serial_col], errors='coerce')

    # 5. 清理临时列并转换数据类型
    df.drop(columns=['is_data_row'], inplace=True)
    for col in df.columns:
        # 再次尝试转换，确保数据类型正确
        if col != serial_col: # 序号列已经处理过
             df[col] = pd.to_numeric(df[col], errors='ignore')

    # 6. 重置索引
    df.reset_index(drop=True, inplace=True)

    return df, structured_metadata


# ===========================================
# 主解析函数
# ===========================================
def intelligent_read_excel(file_path: str, sheet_name: Optional[str | int] = None) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    智能读取Excel文件，自动识别表头、提取元数据并返回清理后的DataFrame。
    """
    metadata = {"source_sheet": sheet_name}
    
    try:
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    except Exception as e:
        metadata["error"] = f"读取Excel文件失败: {e}"
        return None, metadata

    # --- 阶段1: 表头查找 ---
    header_finder = HeaderFinder()
    header_row_index = header_finder.find_header_row_semantic(df_raw)

    if header_row_index == -1:
        print("语义分析失败或未找到高置信度表头，回退到规则分析...")
        header_row_index = find_header_row_rule_based(df_raw)

    if header_row_index == -1:
        metadata["error"] = "无法自动定位表头。请检查文件格式。"
        return None, metadata
    
    metadata['header_row'] = header_row_index

    # --- 阶段2: 创建初始DataFrame ---
    # 确定表头块（处理多行表头）
    header_block = df_raw.iloc[header_row_index:header_row_index + 3] # 假设表头最多占3行
    
    # 合并多行表头
    new_columns = []
    last_valid_col = ''
    for i, col_name in enumerate(header_block.iloc[0]):
        if pd.notna(col_name) and str(col_name).strip():
            last_valid_col = str(col_name).strip().replace('\n', '')
        
        sub_col_names = [str(header_block.iloc[j][i]).strip().replace('\n', '') 
                         for j in range(1, len(header_block)) 
                         if pd.notna(header_block.iloc[j][i])]
        
        full_col_name = ' '.join([last_valid_col] + sub_col_names)
        new_columns.append(full_col_name.strip())

    # 清理和重命名重复列
    final_columns = []
    counts = {}
    for col in new_columns:
        if col in counts:
            counts[col] += 1
            final_columns.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            final_columns.append(col)

    # 创建初始数据帧，包含所有行
    df_initial = df_raw.iloc[header_row_index + len(header_block):].copy()
    df_initial.columns = final_columns
    metadata['columns_found'] = df_initial.columns.tolist()

    # --- 阶段3: 数据清洗与结构化 ---
    df_final, structured_metadata = _clean_and_structure_data(df_initial)
    metadata.update(structured_metadata)
    
    return df_final, metadata
