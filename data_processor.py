import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """
    终极鲁棒解析器：自动校准缺失表头、处理脏字符及列名映射
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    try:
        # 1. 处理 BOM 头
        raw_text = raw_text.encode('utf-8').decode('utf-8-sig')
        
        # 2. 预读：检查第一行是否包含业务关键词。如果不包含，说明可能丢失了表头
        lines = raw_text.strip().split('\n')
        header_line = lines[0]
        
        # 定义我们期望看到的标准列名顺序（对应你 SQL 里的 Select 顺序）
        standard_cols = [
            'Date', 'Campaign Name', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_100_200', # 对应 SQL 结构
            'ECPM_200_300', 'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount'
        ]

        # 如果第一行看起来像数据（例如包含逗号但没有 "Campaign" 或 "Date" 字样）
        if 'Date' not in header_line and 'Campaign' not in header_line:
            # 强制把当前第一行也当做数据读入，并手动指定列名
            df = pd.read_csv(io.StringIO(raw_text), header=None)
            # 仅映射前 N 列（防止 SQL 返回列数与定义不符）
            df.columns = standard_cols[:len(df.columns)]
        else:
            # 正常读取
            df = pd.read_csv(io.StringIO(raw_text), quotechar='"', skipinitialspace=True)
        
        # 3. 彻底清洗列名特殊字符
        df.columns = [re.sub(r'["\'\r\n\t]', '', str(c)).strip() for c in df.columns]
        
        # 4. 关键字段对齐映射（再次兜底）
        mapping = {
            'Cost': ['Cost', 'cost', 'internal_amount_0'],
            'IAP Revenue': ['IAP Revenue', 'iap_revenue', 'internal_amount_7'],
            'Ad Revenue': ['Ad Revenue', 'ad_revenue', 'internal_amount_5']
        }
        for std_name, aliases in mapping.items():
            for col in df.columns:
                if col in aliases:
                    df = df.rename(columns={col: std_name})
                    break

        # 5. 类型强制转换
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        print(f"Data Processor Error: {e}")
        return pd.DataFrame()
