import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    content = raw_text
    try:
        # 针对乱码的终极修复方案
        content = raw_text.encode('latin-1').decode('gbk')
    except:
        pass

    try:
        # 物理对齐表头（注意增加了 Media Source）
        expected_cols = [
            'Date', 'Dimension Value', 'Media Source', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_200_300', 
            'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount', 'group_num_0', 'group_num'
        ]

        df = pd.read_csv(io.StringIO(content.strip()), header=None, quotechar='"', skipinitialspace=True)
        
        # 过滤残留表头行
        if "Date" in str(df.iloc[0,0]) or "Dimension" in str(df.iloc[0,0]):
            df = df.iloc[1:].reset_index(drop=True)
        
        df.columns = expected_cols[:df.shape[1]]

        # 清洗
        df = df.applymap(lambda x: re.sub(r'["\'\r\n\t]', '', str(x)).strip() if isinstance(x, str) else x)

        # 核心数值列转换
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        return df
    except:
        return pd.DataFrame()
