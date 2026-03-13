import pandas as pd
import numpy as np

class DataAnalyser:
    @staticmethod
    def perform_business_analysis(df_raw):
        """
        分析部门核心逻辑：在这里定义所有的业务指标计算
        """
        if df_raw.empty:
            return df_raw
        
        # 1. 深度拷贝，避免影响原始数据
        df = df_raw.copy()
        
        # 2. 字段类型强制转换 (确保所有指标列都是数值型)
        numeric_cols = ['Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV', 'IAP UV']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 3. 计算业务核心指标
        df['Total Revenue'] = df['IAP Revenue'] + df['Ad Revenue']
        
        # 计算 ROI (处理分母为 0 的情况)
        df['ROI'] = df.apply(lambda x: x['Total Revenue'] / x['Cost'] if x['Cost'] > 0 else 0, axis=1)
        
        # 计算单价 (CPI/CPA) - 以 Plot UV 为转化点
        df['CPA_Plot'] = df.apply(lambda x: x['Cost'] / x['Plot UV'] if x['Plot UV'] > 0 else 0, axis=1)
        
        # 计算 ARPU
        df['ARPU'] = df.apply(lambda x: x['Total Revenue'] / x['Plot UV'] if x['Plot UV'] > 0 else 0, axis=1)

        # 4. 数据高亮逻辑 (比如 ROI < 100% 标记为预警)
        # 这里可以根据你的需求增加更多的列
        
        return df

    @staticmethod
    def get_analysis_summary(df_analysed):
        """
        生成分析结论概览
        """
        summary = {
            "总消耗": df_analysed['Cost'].sum(),
            "总营收": df_analysed['Total Revenue'].sum(),
            "综合ROI": df_analysed['Total Revenue'].sum() / df_analysed['Cost'].sum() if df_analysed['Cost'].sum() > 0 else 0,
            "总转化数": df_analysed['Plot UV'].sum()
        }
        return summary
