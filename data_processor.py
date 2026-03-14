import pandas as pd
import numpy as np

class DataAnalyser:
    @staticmethod
    def perform_business_analysis(df_raw):
        """
        分析层：基于 Cohort 逻辑的指标加工
        去掉了 Status 逻辑，仅保留数值计算。
        """
        if df_raw.empty:
            return df_raw
        
        df = df_raw.copy()
        
        # 1. 强制数值化
        numeric_cols = [c for c in df.columns if any(x in c for x in ['UV', 'Revenue', 'Cost', 'ECPM', 'L', 'Times'])]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        # 2. 核心定义计算
        df['Total Revenue'] = df['IAP Revenue'] + df['Ad Revenue']
        df['ROI'] = (df['Total Revenue'] / df['Cost']).replace([np.inf, -np.inf], 0).fillna(0)
        df['CPA_Plot'] = (df['Cost'] / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        df['CPP_Pay'] = (df['Cost'] / df['IAP UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # 3. 辅助质量指标
        high_value_sum = df['ECPM_300_400'] + df['ECPM_400_500'] + df['ECPM_500+']
        df['HV_Rate'] = (high_value_sum / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        df['PUR'] = (df['IAP UV'] / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        return df

    @staticmethod
    def get_summary_metrics(df_analysed):
        """生成顶部汇总数值"""
        if df_analysed.empty: return {}
        
        total_cost = df_analysed['Cost'].sum()
        total_iap_rev = df_analysed['IAP Revenue'].sum()
        total_ad_rev = df_analysed['Ad Revenue'].sum()
        total_rev = total_iap_rev + total_ad_rev
        total_plot = df_analysed['Plot UV'].sum()
        total_iap_uv = df_analysed['IAP UV'].sum()
        
        return {
            "总消耗": total_cost,
            "总营收": total_rev,
            "综合 ROI": total_rev / total_cost if total_cost > 0 else 0,
            "总转化成本": total_cost / total_plot if total_plot > 0 else 0,
            "IAP UV 总数": total_iap_uv,
            "IAP 转化成本": total_cost / total_iap_uv if total_iap_uv > 0 else 0
        }

# 将这段代码添加到 data_processor.py 的最下面（不要放在类里面）

def clean_sql_response(df):
    """
    基础清洗：处理空值、格式化列名，确保 DataFrame 可以被 Streamlit 正常渲染
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # 1. 确保所有列名是字符串
    df.columns = [str(col) for col in df.columns]
    
    # 2. 转换日期格式（如果是字符串则转为 datetime）
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    # 3. 填充空值，避免前端显示 NaN
    df = df.fillna(0)
    
    return df
