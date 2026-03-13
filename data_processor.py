import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """将 CSV 文本转为 DataFrame"""
    if not raw_text:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(raw_text))

def parse_ta_map_column(df, column_name):
    """专门解析数数特有的 {k=v} Map 结构"""
    if df.empty or column_name not in df.columns:
        return pd.DataFrame()
    
    raw_str = df[column_name].iloc[0]
    if not isinstance(raw_str, str):
        return pd.DataFrame()

    # 正则提取 key=value
    items = re.findall(r'([^,=\s]+)=([^,=\s]+)', raw_str.strip("{}"))
    parsed = pd.DataFrame(items, columns=['date', 'value'])
    
    # 类型转换与排序
    parsed['value'] = pd.to_numeric(parsed['value'])
    parsed['date'] = pd.to_datetime(parsed['date']).dt.date
    return parsed.sort_values('date')
