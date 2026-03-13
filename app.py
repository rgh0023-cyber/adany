import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis      # 只负责 SQL 和原始提取
from data_analyser import DataAnalyser  # 专门负责分析逻辑

st.set_page_config(page_title="投放 ROI 分析系统", layout="wide")

# --- 侧边栏 ---
with st.sidebar:
    token = st.text_input("API Token", type="password")
    project_id = st.number_input("项目 ID", value=46)
    dim_choice = st.radio("维度", ["全量汇总", "广告计划", "广告组", "广告创意"])
    d_range = st.date_input("周期", [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()])

# --- 核心流程 ---
if st.button("🔄 刷新数据并执行分析", use_container_width=True):
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s

    # --- 第一步：调用 analysis_lib 获取原始数据 ---
    client = TAClient("https://ta-open.jackpotlandslots.com", token)
    if dim_choice == "全量汇总":
        sql = AdAnalysis.get_absolute_summary_sql(project_id, start_s, end_s)
    else:
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_s, end_s, dim_choice)
    
    raw_text, _ = client.execute_query(sql)
    df_raw = clean_sql_response(raw_text)

    # --- 第二步：上部 - 展现【分析模块】 ---
    st.header("📊 第一部分：数据分析模块")
    # 调用新的分析文件
    df_analysed = DataAnalyser.perform_business_analysis(df_raw)
    
    if not df_analysed.empty:
        metrics = DataAnalyser.get_analysis_summary(df_analysed)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总消耗", f"${metrics['总消耗']:,.2f}")
        c2.metric("总营收", f"${metrics['总营收']:,.2f}")
        c3.metric("综合 ROI", f"{metrics['综合ROI']:.2%}")
        c4.metric("总转化 (Plot)", f"{int(metrics['总转化数']):,}")

        # 展示分析后的表格
        display_cols = ['Date', 'Dimension Value', 'Cost', 'Total Revenue', 'ROI', 'CPA_Plot', 'ARPU']
        st.dataframe(
            df_analysed[display_cols].style.format({
                'Cost': '${:,.2f}', 'Total Revenue': '${:,.2f}', 
                'ROI': '{:.2%}', 'CPA_Plot': '${:.2f}', 'ARPU': '${:.4f}'
            }), 
            use_container_width=True, hide_index=True
        )

    # --- 第三步：下部 - 展现【原始数据】 ---
    st.markdown("---")
    st.header("🔍 第二部分：原始数据展示")
    st.dataframe(df_raw, use_container_width=True)
    
    # 原始数据下载
    st.download_button("📥 下载原始 CSV", df_raw.to_csv(index=False), "raw_data.csv")
