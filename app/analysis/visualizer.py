import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from thefuzz import fuzz
import os

# 设置matplotlib支持中文显示
sns.set_theme(style="whitegrid", font='SimHei', rc={"axes.unicode_minus": False})

def find_items_by_keywords(df: pd.DataFrame, query: str, search_col: str = '项目名称', threshold: int = 70):
    """
    根据关键词和相似度阈值，在DataFrame中智能搜索项目。

    :param df: 要搜索的DataFrame。
    :param query: 用户输入的关键词字符串，以空格分隔。
    :param search_col: 要进行搜索的列名。
    :param threshold: 相似度匹配的阈值 (0-100)。
    :return: 一个包含匹配结果的DataFrame。
    """
    keywords = query.split()
    if not keywords:
        return pd.DataFrame()

    def get_similarity_score(name):
        # 对于每一个项目名称，计算它与所有关键词的平均相似度
        scores = [fuzz.partial_ratio(keyword, name) for keyword in keywords]
        return max(scores) if scores else 0

    df['similarity'] = df[search_col].astype(str).apply(get_similarity_score)
    
    results = df[df['similarity'] >= threshold].copy()
    
    # 如果没有找到任何高于阈值的结果，返回最佳猜测
    if results.empty and not df.empty:
        print(f"未找到高于阈值 {threshold} 的结果，返回最佳猜测。")
        best_guess_idx = df['similarity'].idxmax()
        results = df.loc[[best_guess_idx]].copy()
        
    results.drop(columns=['similarity'], inplace=True)
    return results

def plot_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str, output_path: str):
    """
    创建一个条形图并将其保存到文件。

    :param df: 数据源。
    :param x_col: X轴对应的列。
    :param y_col: Y轴对应的列。
    :param title: 图表标题。
    :param output_path: 图片保存路径。
    """
    if df.empty:
        print("数据为空，无法生成条形图。")
        return

    plt.figure(figsize=(12, 8))
    sns.barplot(data=df, x=x_col, y=y_col)
    plt.title(title, fontsize=16)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout() # 调整布局以防标签重叠
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    print(f"图表已保存至: {output_path}")
    plt.close()

# 未来可以继续在这里添加 plot_pie_chart, plot_line_chart 等函数
