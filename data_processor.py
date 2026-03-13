import pandas as pd
import io

def clean_sql_response(raw_text):
    """清洗 CSV 并强制标准化所有列名"""
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    
    try:
        # 读取 CSV
        df = pd.read_csv(io.StringIO(raw_text))
        
        # 核心修复：移除列名中的双引号、单引号及首尾空格
        # 解决 SQL 别名 "Cost" 变成 Pandas 列名 '"Cost"' 的问题
        df.columns = [
            str(c).replace('"', '').replace("'", "").strip() 
            for c in df.columns
        ]
        
        # 将 Date 列转换为标准日期格式（如果存在）
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
        return df
    except Exception as e:
        print(f"Data processing error: {e}")
        return pd.DataFrame()
