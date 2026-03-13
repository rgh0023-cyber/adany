import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """
    终极鲁棒解析器：自动处理 BOM 头、引号嵌套、特殊字符、以及列名不规范问题
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    try:
        # 1. 预处理：去掉可能导致首列解析失败的 UTF-8 BOM 头
        raw_text = raw_text.encode('utf-8').decode('utf-8-sig')
        
        # 2. 读取 CSV，自动处理引号
        df = pd.read_csv(io.StringIO(raw_text), quotechar='"', skipinitialspace=True)
        
        # 3. 核心修复：深度清洗列名
        new_columns = []
        for col in df.columns:
            # 去掉所有引号、换行符、制表符
            clean_name = re.sub(r'["\'\r\n\t]', '', str(col)).strip()
            new_columns.append(clean_name)
        df.columns = new_columns
        
        # 4. 模糊匹配映射 (防止 TA 返回的是 "Cost" 而代码找 Cost)
        # 我们建立一个映射关系，只要列名里包含这些关键词就强制更名
        mapping = {
            'Cost': ['Cost', 'cost', 'internal_amount_0', '消耗'],
            'IAP Revenue': ['IAP Revenue', 'iap_revenue', 'IAP营收'],
            'Ad Revenue': ['Ad Revenue', 'ad_revenue', '广告营收'],
            'Plot UV': ['Plot UV', 'plot_uv', 'internal_amount_1']
        }
        
        current_cols = df.columns.tolist()
        final_mapping = {}
        
        for standard_name, aliases in mapping.items():
            for col in current_cols:
                if col == standard_name or col in aliases:
                    final_mapping[col] = standard_name
                    break
        
        if final_mapping:
            df = df.rename(columns=final_mapping)

        # 5. 类型强制转换
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df
    except Exception as e:
        print(f"解析发生异常: {e}")
        return pd.DataFrame()
