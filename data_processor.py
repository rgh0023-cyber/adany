import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    # --- 强力解码逻辑开始 ---
    # 如果输入是 bytes，先尝试 utf-8，不行再尝试 gbk
    if isinstance(raw_text, bytes):
        try:
            content = raw_text.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_text.decode('gbk', errors='ignore')
    else:
        # 如果已经是字符串，但看起来像乱码（ISO-8859-1 误认 UTF-8）
        try:
            content = raw_text.encode('iso-8859-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            content = raw_text
    # --- 强力解码逻辑结束 ---

    try:
        # 定义物理对齐表头
        expected_cols = [
            'Date', 'Dimension Value', 'Media Source', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_200_300', 
            'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount', 'group_num_0', 'group_num'
        ]

        # 使用 StringIO 读取，显式指定引擎
        df = pd.read_csv(
            io.StringIO(content.strip()), 
            header=None, 
            quotechar='"', 
            skipinitialspace=True,
            engine='python'
        )
        
        # 过滤第一行是表头字符的情况
        if df.shape[0] > 0 and ("Date" in str(df.iloc[0,0]) or "Dimension" in str(df.iloc[0,0])):
            df = df.iloc[1:].reset_index(drop=True)
        
        # 强制对齐列名
        df.columns = expected_cols[:df.shape[1]]

        # 清洗特殊字符
        def clean_val(x):
            if isinstance(x, str):
                return re.sub(r'["\'\r\n\t]', '', x).strip()
            return x

        df = df.applymap(clean_val)

        # 核心指标转数值
        numeric_cols = ['Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        return df
    except Exception as e:
        print(f"解析错误: {e}")
        return pd.DataFrame()
