import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis
from data_analyser import DataAnalyser

st.set_page_config(page_title="ROI 智能分析系统", layout="wide")

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 配置")
    token = st.text_input("TA API Token", type="password")
    project_id = st.number_input("项目 ID", value=46)
    st.markdown("---")
    dim_choice = st.radio("统计维度", ["全量汇总", "广告计划", "广告组", "广告创意"])
    st.markdown("---")
    d_range = st.date_input("Cohort 周期", [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()])

# --- 核心逻辑 ---
if st.button("🚀 执行分析", use_container_width=True):
    if not token:
        st.warning("请输入 Token")
        st.stop()
    
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s

    client = TAClient("https://ta-open.jackpotlandslots.com", token)
    
    with st.spinner("正在提取 Cohort 数据..."):
        if dim_choice == "全量汇总":
            sql = AdAnalysis.get_absolute_summary_sql(project_id, start_s, end_s)
        else:
            sql = AdAnalysis.get_advertising_report_sql(project_id, start_s, end_s, dim_choice)
        
        raw_text, error = client.execute_query(sql)
        if error:
            st.error(error)
            st.stop()
        df_raw = clean_sql_response(raw_text)

    if not df_raw.empty:
        # 第一部分：业务分析层
        st.header("📊 业务分析层 (Cohort Based)")
        
        df_analysed = DataAnalyser.perform_business_analysis(df_raw)
        m = DataAnalyser.get_summary_metrics(df_analysed)

        # 核心指标卡片
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("总消耗", f"${m['总消耗']:,.2f}")
        c2.metric("总营收", f"${m['总营收']:,.2f}")
        c3.metric("综合 ROI", f"{m['综合 ROI']:.2%}")
        c4.metric("激活成本(CPA)", f"${m['总转化成本']:.2f}")
        c5.metric("IAP UV", f"{int(m['IAP UV 总数']):,}")
        c6.metric("IAP 转化成本", f"${m['IAP 转化成本']:.2f}")

        # 分析表格 (按照要求去掉了 Status 和 ROI 颜色)
        st.subheader("维度穿透视图")
        view_cols = ['Date', 'Dimension Value', 'Cost', 'Total Revenue', 'ROI', 'CPA_Plot', 'IAP UV', 'CPP_Pay', 'HV_Rate', 'PUR']
        
        st.dataframe(
            df_analysed[view_cols].style.format({
                'Cost': '${:,.2f}', 'Total Revenue': '${:,.2f}', 'ROI': '{:.2%}',
                'CPA_Plot': '${:.2f}', 'IAP UV': '{:,.0f}', 'CPP_Pay': '${:.2f}',
                'HV_Rate': '{:.1%}', 'PUR': '{:.2%}'
            }),
            use_container_width=True, hide_index=True
        )

        # 第二部分：对账层
        st.markdown("---")
        with st.expander("🔍 原始数据明细 (对账/下载)"):
            st.dataframe(df_raw, use_container_width=True)
            csv = df_raw.to_csv(index=False).encode('utf-8')
            st.download_button("📥 下载原始报表", data=csv, file_name=f"cohort_raw.csv", mime="text/csv")
    else:
        st.info("暂无数据")
