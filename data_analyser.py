import pandas as pd
import numpy as np

class DataAnalyser:
    @staticmethod
    def perform_business_analysis(df_raw):
        """
        分析层：基于 Cohort 逻辑的指标加工
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
        
        # ROI 计算 (避免除以0)
        df['ROI'] = (df['Total Revenue'] / df['Cost']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # 总转化成本 (CPA) -> 每一记 Plot UV 的成本
        df['CPA_Plot'] = (df['Cost'] / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # IAP 转化成本 (CPP) -> 每一个付费用户的获取成本
        df['CPP_Pay'] = (df['Cost'] / df['IAP UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # 3. 辅助质量指标 (Cohort 深度)
        # 高价值用户占比 (ECPM > 300)
        high_value_sum = df['ECPM_300_400'] + df['ECPM_400_500'] + df['ECPM_500+']
        df['HV_Rate'] = (high_value_sum / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # 付费率 (PUR)
        df['PUR'] = (df['IAP UV'] / df['Plot UV']).replace([np.inf, -np.inf], 0).fillna(0)
        
        # 基于原始 SQL 列做衍生：仅当原始表存在对应列时才增加展示用列
        if 'L20 UV' in df.columns and 'Plot UV' in df.columns:
            # 20关通过率 = L20 UV / Plot UV，分母为0为空值
            df['L20_Pass_Rate'] = np.where(df['Plot UV'] == 0, np.nan, df['L20 UV'] / df['Plot UV'])
            df['L20_Pass_Rate'] = df['L20_Pass_Rate'].replace([np.inf, -np.inf], np.nan)
        if 'L20 UV' in df.columns and 'Cost' in df.columns:
            # 20关成本 = Cost / L20 UV，分母为0为空值
            df['CPA_L20'] = np.where(df['L20 UV'] == 0, np.nan, df['Cost'] / df['L20 UV'])
            df['CPA_L20'] = df['CPA_L20'].replace([np.inf, -np.inf], np.nan)
        
        # 4. 状态评分逻辑
        def get_status(row):
            if row['Cost'] < 30: return "⚪ 样本不足"
            if row['ROI'] >= 1.0: return "🟢 盈利"
            if row['ROI'] >= 0.8: return "🟡 回本边缘"
            return "🔴 亏损"
        
        df['Status'] = df.apply(get_status, axis=1)
        
        return df

    @staticmethod
    def get_summary_metrics(df_analysed):
        """
        生成顶部汇总卡片的核心数值
        """
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
            "IAP 转化成本": total_cost / total_iap_uv if total_iap_uv > 0 else 0,
            "内购占比": total_iap_rev / total_rev if total_rev > 0 else 0
        }
