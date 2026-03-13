import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """将 CSV 文本转为 DataFrame"""
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    
    try:
        # 强制指定表头，或者让 pandas 自动推断
        df = pd.read_csv(io.StringIO(raw_text))
        return df
    except Exception:
        return pd.DataFrame()

def parse_ta_map_column(df, column_name):
    """
    专门解析数数 Map 结构: {2026-03-11 00:00:00.000=1261.0, ...}
    """
    if df.empty:
        return pd.DataFrame()
    
    # 自动获取第一列内容（如果 column_name 匹配不上）
    raw_str = ""
    if column_name in df.columns:
        raw_str = str(df[column_name].iloc[0])
    else:
        raw_str = str(df.iloc[0, 0])

    if not raw_str or raw_str == "nan":
        return pd.DataFrame()

    # 正则优化：匹配 [非等号非逗号] = [非逗号非右括号]
    items = re.findall(r'([^=,{}]+)=([^,{}]+)', raw_str.strip("{}"))
    
    if not items:
        return pd.DataFrame()
        
    processed_items = []
    for k, v in items:
        processed_items.append({
            "date": k.strip(), 
            "value": float(v.strip())
        })
        
    parsed = pd.DataFrame(processed_items)
    
    # 时间转换：将 "2026-03-11 00:00:00.000" 转换为 "2026-03-11"
    parsed['date'] = pd.to_datetime(parsed['date']).dt.date
    return parsed.sort_values('date')
