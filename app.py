import streamlit as st
import datetime
import pandas as pd
# 确保以下自定义模块在同一目录下
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis
from data_analyser import DataAnalyser

# 1. 页面基础配置
st.set_page_config(
    page_title="ROI 智能分析系统 (Cohort)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. 侧边栏配置 ---
def _get_token():
    """优先从 Streamlit Secrets 读取 Token，否则使用侧边栏输入"""
    try:
        token = st.secrets.get("ta_api_token", "")
        if token:
            return token
        ta = st.secrets.get("ta") or {}
        if isinstance(ta, dict):
            return ta.get("token", "")
    except (FileNotFoundError, AttributeError, TypeError):
        pass
    return ""

with st.sidebar:
    st.header("⚙️ 数据源配置")
    token_from_secrets = _get_token()
    if token_from_secrets:
        st.caption("✅ 已使用已配置的 TA API Token（来自 Secrets）")
        token = token_from_secrets
        token_override = st.text_input("TA API Token（留空则使用上方已配置）", type="password", help="临时覆盖时在此输入")
        if token_override:
            token = token_override
    else:
        token = st.text_input("TA API Token", type="password", help="请输入数数科技 API 调用令牌，或配置 .streamlit/secrets.toml")
    project_id = st.number_input("项目 ID", value=46)
    
    st.markdown("---")
    st.header("🔍 查询维度")
    dim_choice = st.radio(
        "选择统计维度", 
        ["全量汇总", "广告计划", "广告组", "广告创意"],
        index=0
    )
    
    st.markdown("---")
    st.header("📅 Cohort 周期")
    # 默认选择最近 7 天
    default_start = datetime.date.today() - datetime.timedelta(days=7)
    default_end = datetime.date.today()
    d_range = st.date_input("选择新增批次范围", [default_start, default_end])

# --- 3. 核心逻辑执行 ---
if st.button("🚀 执行 Cohort 深度分析", use_container_width=True):
    if not token:
        st.warning("⚠️ 请先在侧边栏输入 API Token")
        st.stop()
    
    # 解析日期范围
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s

    # 初始化客户端
    client = TAClient("https://ta-open.jackpotlandslots.com", token)
    
    with st.spinner(f"正在分析 {start_s} 至 {end_s} 的新增批次数据..."):
        # 获取 SQL (已在 analysis_lib 中更新为 Cohort 逻辑)
        if dim_choice == "全量汇总":
            sql = AdAnalysis.get_absolute_summary_sql(project_id, start_s, end_s)
        else:
            sql = AdAnalysis.get_advertising_report_sql(project_id, start_s, end_s, dim_choice)
        
        # 执行查询
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"❌ SQL 执行错误: {error}")
            st.stop()
        
        # 清洗数据
        df_raw = clean_sql_response(raw_text)

    if df_raw.empty:
        st.info("📭 该范围内暂无新增用户数据")
        st.stop()

    # --- 第一部分：上部 - 业务分析层 (Analysis Module) ---
    st.header("📊 业务分析层 (Cohort Based)")
    st.caption(f"分析逻辑：锁定 {start_s} ~ {end_s} 新增用户，统计其从激活至今的累积价值")

    # 加工数据
    df_analysed = DataAnalyser.perform_business_analysis(df_raw)
    metrics = DataAnalyser.get_summary_metrics(df_analysed)

    # 1.1 顶部核心卡片
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("总消耗 (Cost)", f"${metrics['总消耗']:,.2f}")
    c2.metric("总营收 (Gross)", f"${metrics['总营收']:,.2f}")
    c3.metric("综合 ROI", f"{metrics['综合 ROI']:.2%}")
    c4.metric("总转化成本(CPA)", f"${metrics['总转化成本']:.2f}")
    c5.metric("IAP UV", f"{int(metrics['IAP UV 总数']):,}")
    c6.metric("IAP 转化成本", f"${metrics['IAP 转化成本']:.2f}")

    # 1.2 分析表格
    st.subheader("维度穿透视图")
    view_cols = [
        'Date', 'OS', 'Dimension Value', 'Cost', 'Total Revenue', 
        'ROI', 'CPA_Plot', 'IAP UV', 'CPP_Pay', 'HV_Rate', 'PUR'
    ]
    
    # 映射更友好的列名
    display_df = df_analysed[view_cols].rename(columns={
        'Dimension Value': '维度名称',
        'CPA_Plot': '激活成本',
        'CPP_Pay': '付费成本',
        'HV_Rate': '高价值率',
        'PUR': '付费率'
    })

    st.dataframe(
        display_df.style.format({
            'Cost': '${:,.2f}', 'Total Revenue': '${:,.2f}', 'ROI': '{:.2%}',
            '激活成本': '${:.2f}', 'IAP UV': '{:,.0f}', '付费成本': '${:.2f}',
            '高价值率': '{:.1%}', '付费率': '{:.2%}'
        }),
        use_container_width=True, hide_index=True
    )

    # --- 第二部分：下部 - 原始数据对账层 (Source Data) ---
    st.markdown("---")
    with st.expander("🔍 原始数据明细 (对账专用)", expanded=False):
        st.write("此处展示 SQL 返回的原始字段（含 ECPM 分布及 L 等级 UV）")
        st.dataframe(df_raw, use_container_width=True)
        
        # 导出功能
        csv = df_raw.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下载原始报表 (.csv)",
            data=csv,
            file_name=f"cohort_{dim_choice}_{start_s}_to_{end_s}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    # 初始状态提示
    st.info("👈 请在左侧侧边栏配置 Token 和 Cohort 周期，然后点击执行分析。")
    
    # 展示分析定义说明
    with st.expander("📚 指标定义说明"):
        st.write("""
        - **总转化成本 (CPA)**: `总消耗 / Plot UV` (获取每个激活用户的成本)
        - **IAP 转化成本 (CPP)**: `总消耗 / IAP UV` (获取每个付费用户的成本)
        - **ROI**: `(内购净营收 + 广告营收) / 总消耗`
        - **高价值率**: ECPM > 300 的用户占比
        """)
