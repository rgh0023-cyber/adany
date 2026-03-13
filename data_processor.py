import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """将 CSV 文本转为 DataFrame，不假设有表头"""
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    
    try:
        # header=None 表示 CSV 没表头，第一行就是数据
        df = pd.read_csv(io.StringIO(raw_text), header=None)
        return df
    except Exception:
        return pd.DataFrame()

def parse_ta_map_column(df, column_name=None):
    """
    通过索引位置解析 Map 结构，解决无表头问题
    """
    if df.empty:
        return pd.DataFrame()
    
    # 无论有没有表头，直接取第一行、第一列的内容
    # 因为你的原始响应显示数据就在最开始
    raw_str = str(df.iloc[0, 0])

    if not raw_str or raw_str == "nan" or "{" not in raw_str:
        return pd.DataFrame()

    # 改进正则：匹配 [非等号非逗号] = [数字/浮点数]
    # 能够精准捕获 "2026-03-11 00:00:00.000=1261.0"
    items = re.findall(r'([^=,{}]+)=([-+]?\d*\.\d+|\d+)', raw_str.strip("{}"))
    
    if not items:
        return pd.DataFrame()
        
    processed_items = []
    for k, v in items:
        processed_items.append({
            "date": k.strip(), 
            "value": float(v.strip())
        })
        
    parsed = pd.DataFrame(processed_items)
    
    # 将带毫秒的字符串转为纯日期
    parsed['date'] = pd.to_datetime(parsed['date']).dt.date
    return parsed.sort_values('date')
