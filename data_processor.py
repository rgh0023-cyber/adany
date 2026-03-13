import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    try:
        content = raw_text.encode('utf-8').decode('utf-8-sig').strip()
        
        # 定义 SQL 严格的物理列顺序 (核心防御)
        expected_cols = [
            'Date', 'Campaign Name', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_199_200_alt',
            'ECPM_200_300', 'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount', 'group_num_0', 'group_num'
        ]

        # 尝试读取
        df = pd.read_csv(io.StringIO(content), quotechar='"', skipinitialspace=True)
        
        # 如果第一列看起来像日期（数据）而不是字符串"Date"，判定表头丢失
        first_val = str(df.columns[0])
        if not re.search(r'[a-zA-Z]', first_val) or (re.match(r'\d{4}-\d{2}-\d{2}', first_val)):
            df = pd.read_csv(io.StringIO(content), header=None, quotechar='"')
            df.columns = expected_cols[:len(df.columns)]
        else:
            df.columns = [re.sub(r'["\'\r\n\t]', '', str(c)).strip() for c in df.columns]

        # 别名二次对齐
        mapping = {'Cost':['internal_amount_0'], 'IAP Revenue':['internal_amount_7'], 'Ad Revenue':['internal_amount_5']}
        for std, aliases in mapping.items():
            for col in df.columns:
                if col in aliases:
                    df = df.rename(columns={col: std})
        
        # 数值转换
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        return df
    except:
        return pd.DataFrame()
