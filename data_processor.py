import pandas as pd
import numpy as np
import io  # 必须引入，用于处理文本流

def clean_sql_response(raw_text):
    """
    基础清洗：
    1. 修复崩溃：将 API 返回的 CSV 字符串转换为 DataFrame
    2. 格式化：统一列名、日期和填充空值
    """
    # 如果 raw_text 不是字符串或为空，直接返回空表，防止 AttributeError
    if not isinstance(raw_text, str) or not raw_text.strip():
        return pd.DataFrame()

    try:
        # --- 核心修复：把文本转成表格 ---
        df = pd.read_csv(io.StringIO(raw_text))
        
        # 此时 df 已经是 DataFrame 对象，可以安全使用 .empty 了
        if df.empty:
            return pd.DataFrame()
        
        # 1. 强制列名转为字符串 (防止 SQL 别名导致的问题)
        df.columns = [str(col) for col in df.columns]
        
        # 2. 转换日期格式 (保持昨天调通后的展示格式)
        if 'Date' in df.columns:
            # 兼容各种日期格式，统一只保留 YYYY-MM-DD
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
        # 3. 填充空值，避免 Streamlit 报错
        df = df.fillna(0)
        
        return df
        
    except Exception as e:
        # 即使解析报错，也要返回空表让 app.py 继续运行，而不是直接崩溃
        print(f"解析 CSV 数据失败: {e}")
        return pd.DataFrame()

# 如果你的代码里还有 DataAnalyser 类，可以保持在下方，或者只保留这个函数
