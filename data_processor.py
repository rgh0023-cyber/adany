import pandas as pd
import io

def clean_sql_response(raw_text):
    """直接将 CSV 响应转化为 DataFrame，现在的 SQL 返回的是多行多列的标准表格"""
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    
    try:
        # 现在的 SQL 是标准报表，通常自带表头
        df = pd.read_csv(io.StringIO(raw_text))
        # 自动清理列名中可能的引号
        df.columns = [c.replace('"', '').strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# 此前的 parse_ta_map_column 在这条 SQL 中不再需要，可以保留作为工具函数
