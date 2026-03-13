import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 看板", layout="wide")

st.title("🎯 广告投放多维归因报表")

with st.sidebar:
    token = st.text_input("Token", type="password")
    api_url = st.text_input("URL", value="https://ta-open.jackpotlandslots.com")
    project_id = 46
    d_range = st.date_input("分析周期", [datetime.date(2026, 3, 3), datetime.date(2026, 3, 12)])

if st.button("生成归因报表", use_container_width=True):
    with st.status("正在进行大规模多维归因计算...", expanded=True) as status:
        
        st.write("1️⃣ 构建归因 SQL...")
        sql = AdAnalysis.get_advertising_report_sql(
            project_id, 
            d_range[0].strftime('%Y-%m-%d'), 
            d_range[1].strftime('%Y-%m-%d')
        )
        
        st.write("2️⃣ 请求接口中 (此 SQL 涉及多表 Join，请耐心等待)...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"查询失败: {error}")
            status.update(label="❌ 任务失败", state="error")
            st.stop()
            
        st.write("3️⃣ 数据结构化处理...")
        df = clean_sql_response(raw_text)
        
        if df.empty:
            st.warning("查询成功但无数据。请确认对应日期内是否有 appsflyer_master_data 事件。")
            status.update(label="⚠️ 无数据", state="error")
            st.stop()
            
        status.update(label="✅ 报表生成成功", state="complete", expanded=False)

    # --- 核心数据看板 ---
    st.divider()
    
    # 计算汇总指标
    total_cost = df['Cost'].sum()
    total_iap = df['IAP Revenue'].sum()
    total_ad = df['Ad Revenue'].sum()
    total_revenue = total_iap + total_ad
    roi = (total_revenue / total_cost) if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗 (Cost)", f"${total_cost:,.2f}")
    c2.metric("总总收 (Gross)", f"${total_revenue:,.2f}")
    c3.metric("ROI", f"{roi:.2%}", delta=f"{roi-1:.2%}")
    c4.metric("广告变现占比", f"{(total_ad/total_revenue):.1%}" if total_revenue > 0 else "0%")

    st.subheader("📋 详细投放明细")
    # 允许用户按系列搜索
    search_query = st.text_input("过滤 Campaign Name...")
    if search_query:
        display_df = df[df['Campaign Name'].str.contains(search_query, case=False)]
    else:
        display_df = df

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 简单的可视化：消耗与营收对比
    st.subheader("📈 消耗与总营收趋势")
    trend_df = df.groupby('Date')[['Cost', 'Ad Revenue', 'IAP Revenue']].sum()
    st.area_chart(trend_df)
