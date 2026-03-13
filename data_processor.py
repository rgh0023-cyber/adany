import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(raw_text))

def parse_ta_map_column(df, column_name):
    if df.empty or column_name not in df.columns:
        return pd.DataFrame()
    
    raw_str = df[column_name].iloc[0]
    if not isinstance(raw_str, str):
        return pd.DataFrame()

    items = re.findall(r'([^,=\s]+)=([^,=\s]+)', raw_str.strip("{}"))
    if not items:
        return pd.DataFrame()
        
    parsed = pd.DataFrame(items, columns=['date', 'value'])
    parsed['value'] = pd.to_numeric(parsed['value'])
    parsed['date'] = pd.to_datetime(parsed['date']).dt.date
    return parsed.sort_values('date')
