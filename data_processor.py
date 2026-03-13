import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """
    将 CSV 文本转为 DataFrame。
    注意：数数返回的 CSV 可能会有引号包裹，pandas 会自动处理。
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    
    # 针对你提供的数据格式，这里确保第一行被正确解析
    # 如果 CSV 没有表头，可以手动指定，但通常 TA 的 SQL 接口第一行是字段名
    try:
        df = pd.read_csv(io.StringIO(raw_text))
        return df
    except Exception as e:
        # 如果 read_csv 失败，尝试手动解析首行
        return pd.DataFrame()

def parse_ta_map_column(df, column_name):
    """
    专门解析数数 Map 结构: {2026-03-11 00:00:00.000=1261.0, ...}
    """
    if df.empty:
        return pd.DataFrame()
    
    # 如果 DataFrame 有表头，按名称取；如果没有，取第一列
    raw_str = ""
    if column_name in df.columns:
        raw_str = str(df[column_name].iloc[0])
    else:
        raw_str = str(df.iloc[0, 0])

    if not raw_str or raw_str == "nan":
        return pd.DataFrame()

    # 更新正则表达式：
    # ([^=]+) 匹配等号左边所有非等号字符（包含空格和点）
    # = 匹配等号
    # ([^, }]+) 匹配等号右边直到逗号或花括号为止的内容
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
    
    # 进一步清洗日期：只保留 YYYY-MM-DD
    parsed['date'] = pd.to_datetime(parsed['date']).dt.date
    parsed = parsed.sort_values('date')
    
    return parsed
