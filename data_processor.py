import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    try:
        # 再次尝试在字符串层面去除常见的乱码标志
        content = raw_text.strip()
        
        # 物理对齐表头（根据 SQL 顺序）
        expected_cols = [
            'Date', 'Campaign Name', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_200_300', 
            'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount', 'group_num_0', 'group_num'
        ]

        # 尝试使用逗号读取，如果不成尝试制表符
        try:
            df = pd.read_csv(io.StringIO(content), header=None, quotechar='"', skipinitialspace=True)
        except:
            df = pd.read_csv(io.StringIO(content), header=None, sep='\t')
        
        # 判断第一行是不是残留的英文字符表头
        if "Date" in str(df.iloc[0,0]) or "date" in str(df.iloc[0,0]).lower():
            df = df.iloc[1:].reset_index(drop=True)
        
        # 强制指定列名
        df.columns = expected_cols[:len(df.columns)]

        # 深度清洗：去除引号、乱码不可见字符
        def scrub_text(val):
            if isinstance(val, str):
                # 过滤掉非打印字符，但保留中文和常用标点
                return re.sub(r'["\'\r\n\t]', '', val).strip()
            return val

        df = df.applymap(scrub_text)

        # 数值转换
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        return df
    except Exception as e:
        print(f"Processor Error: {e}")
        return pd.DataFrame()
