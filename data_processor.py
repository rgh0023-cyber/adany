import pandas as pd
import io
import re

def clean_sql_response(raw_text):
    """
    终极版：解决中文乱码 + 自动强制表头对齐
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return pd.DataFrame()

    try:
        # 1. 强制使用 utf-8-sig 解码，解决 BOM 头导致的中文或首列乱码
        if isinstance(raw_text, bytes):
            content = raw_text.decode('utf-8-sig', errors='ignore').strip()
        else:
            # 如果已经是字符串，重新编码再用 sig 解码，这是修正乱码的常用技巧
            content = raw_text.encode('utf-8').decode('utf-8-sig', errors='ignore').strip()
        
        # 2. 定义 SQL 严格的物理列顺序 (必须与 AdAnalysis SELECT 顺序 100% 对应)
        expected_cols = [
            'Date', 'Campaign Name', 'OS', 'Cost', 'Plot UV', 
            'ECPM_Null', 'ECPM_0_100', 'ECPM_100_200', 'ECPM_200_300', 
            'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+',
            'L10 UV', 'L20 UV', 'L30 UV', 'L40 UV', 'L50 UV', 'L60 UV', 'L70 UV', 'L80 UV', 'L90 UV', 'L100 UV',
            'IAP UV', 'IAP Times', 'IAP Revenue', 'Ad UV', 'Ad Revenue', 'total_amount', 'group_num_0', 'group_num'
        ]

        # 3. 第一次尝试：不读表头，直接读所有内容（最暴力也最保险）
        df = pd.read_csv(io.StringIO(content), header=None, quotechar='"', skipinitialspace=True)
        
        # 4. 逻辑判断：如果第一行内容其实是 "Date" 字符串，说明有表头，我们要删掉第一行
        # 如果第一行是 "2026-xx-xx" 这样的数据，说明没表头，直接用
        first_cell = str(df.iloc[0, 0])
        if "Date" in first_cell or "date" in first_cell.lower():
            df = df.iloc[1:].reset_index(drop=True)
        
        # 5. 强制贴上我们定义的中文和英文表头
        df.columns = expected_cols[:len(df.columns)]

        # 6. 清洗数据中的所有单元格（去除残留的引号、换行、或乱码残余）
        def deep_clean(val):
            if isinstance(val, str):
                # 去掉引号和换行
                val = re.sub(r'["\'\r\n\t]', '', val).strip()
                return val
            return val

        df = df.applymap(deep_clean)

        # 7. 数值类型转换
        numeric_cols = ['Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        print(f"数据清洗严重异常: {e}")
        return pd.DataFrame()
