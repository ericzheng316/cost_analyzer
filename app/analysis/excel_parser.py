import pandas as pd
import numpy as np
import io
from typing import Optional

def get_row_score(row, header_keywords):
    """Scores a single row based on how likely it is to be a header."""
    score = 0
    non_empty_cells = row.dropna()
    non_empty_count = len(non_empty_cells)
    if non_empty_count == 0: return 0
    if non_empty_count < 3 and any(len(str(c)) > 10 for c in non_empty_cells): return -100
    keyword_count = sum(1 for cell in non_empty_cells for keyword in header_keywords if keyword in str(cell).lower())
    score += 5 * keyword_count
    if len(row) > 0:
        non_empty_ratio = non_empty_count / len(row)
        if non_empty_ratio > 0.4: score += 10 * non_empty_ratio
    string_like_count = sum(isinstance(c, str) for c in non_empty_cells)
    if non_empty_count > 0:
        string_ratio = string_like_count / non_empty_count
        if string_ratio > 0.8: score += 10 * string_ratio
    if non_empty_count > 0 and non_empty_count == len(set(non_empty_cells)): score += 10
    return score

def intelligent_read_excel(source: str | io.BytesIO, sheet_name: Optional[str | int] = None):
    """
    Intelligently reads an Excel file, supporting file paths or in-memory objects. (V19 - Auto Sheet Detection)
    If sheet_name is None, it automatically finds the best sheet.
    Returns a tuple (DataFrame, dict) or (None, dict) with an error.
    """
    header_keywords = ['项目', '名称', '单价', '数量', '总价', '合计', '单位', '品牌', '规格', '型号', '备注', '序号', '类别']
    
    try:
        excel_file = pd.ExcelFile(source)
        sheet_names = excel_file.sheet_names
        
        target_sheet_name = sheet_name
        df_head = None

        if target_sheet_name is None:
            print("`sheet_name` is None, attempting to find the best sheet...")
            if not sheet_names:
                return None, {"error": "Excel file contains no sheets."}

            best_sheet_candidate = None
            max_score = -1
            best_df_head = None

            for s_name in sheet_names:
                try:
                    df_preview = pd.read_excel(excel_file, sheet_name=s_name, header=None, nrows=20)
                    if df_preview.empty:
                        continue
                    
                    scores = [get_row_score(row, header_keywords) for _, row in df_preview.iterrows()]
                    current_max_score = np.max(scores)

                    if current_max_score > max_score:
                        max_score = current_max_score
                        best_sheet_candidate = s_name
                        best_df_head = df_preview
                except Exception as sheet_error:
                    print(f"Could not read or score sheet '{s_name}'. Error: {sheet_error}")
                    continue
            
            if best_sheet_candidate is None:
                return None, {"error": "Could not find a suitable sheet with a recognizable header."}
            
            target_sheet_name = best_sheet_candidate
            df_head = best_df_head
            print(f"Best sheet found: '{target_sheet_name}' with score {max_score:.1f}")

        if df_head is None:
            df_head = pd.read_excel(excel_file, sheet_name=target_sheet_name, header=None, nrows=20)

        if df_head.empty:
            return None, {"error": f"Sheet '{target_sheet_name}' is empty."}

        scores = [get_row_score(row, header_keywords) for _, row in df_head.iterrows()]
        header_start = np.argmax(scores)
        print(f"Detected header block start: {header_start} (Score: {scores[header_start]:.1f})")

        header_end = header_start
        for i in range(header_start + 1, len(df_head)):
            row = df_head.iloc[i]
            is_grouping_row = pd.isna(row.iloc[0]) and pd.notna(row.iloc[1]) and pd.isna(row.iloc[2])
            if is_grouping_row:
                header_end = i - 1
                print(f"Header block ends at row {header_end} (found data grouping row)")
                break
            header_end = i

        header_rows = list(range(header_start, header_end + 1))
        print(f"Final header rows determined: {header_rows}")

        df = pd.read_excel(excel_file, sheet_name=target_sheet_name, header=header_rows)
        df.dropna(axis=1, how='all', inplace=True)

        new_cols = []
        metadata = {"formulas": {}, "codes": {}, "source_sheet": target_sheet_name}
        for col in df.columns:
            cleaned_levels = []
            for level in col:
                level_str = str(level)
                if 'Unnamed' in level_str: continue
                parts = level_str.strip().split('\n')
                base_name = parts[0].strip()
                if len(parts) > 1 and parts[1].strip().startswith('('):
                    base_name += parts[1].strip()
                cleaned_levels.append(base_name)

            if not cleaned_levels: new_cols.append(''); continue

            levels = cleaned_levels
            formula = next((lvl for lvl in levels if '=' in lvl), None)
            code = levels[-1] if len(levels[-1]) == 1 and levels[-1].isalpha() else None
            name_candidates = [lvl for lvl in levels if lvl != formula and lvl != code]
            column_name = name_candidates[-1] if name_candidates else levels[-1]
            new_cols.append(column_name)

            if formula: metadata["formulas"][column_name] = formula
            if code: metadata["codes"][code] = column_name
        
        df.columns = new_cols
        print("Successfully extracted and cleaned column names.")

        grouping_col_name = '功能区'
        anchor_col_name = '项目名称'
        if grouping_col_name in df.columns and anchor_col_name in df.columns:
            print("Found hierarchical structure, starting layered filling...")
            is_l1_label_row = df[anchor_col_name].isna()
            l1_labels = df[grouping_col_name].where(is_l1_label_row)
            l1_col_name = f"{grouping_col_name}_L1"
            l2_col_name = f"{grouping_col_name}_L2"
            df.insert(df.columns.get_loc(grouping_col_name), l1_col_name, l1_labels.ffill())
            df.rename(columns={grouping_col_name: l2_col_name}, inplace=True)
            df.loc[is_l1_label_row, l2_col_name] = np.nan
            df.dropna(subset=[anchor_col_name], inplace=True)
            print("Layered filling complete, generated L1 and L2 functional areas.")

        df.reset_index(drop=True, inplace=True)
        return df, metadata

    except Exception as e:
        print(f"An error occurred during Excel file processing: {e}")
        error_msg = f"File processing failed: {e}. Please ensure it's a valid Excel file."
        if not isinstance(source, io.BytesIO):
            error_msg = f"File path processing failed: {e}"
        return None, {"error": error_msg}
