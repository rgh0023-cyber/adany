import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统", layout="wide")
st.title("🎯 广告投放多维归因报表")

# --- 1. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    st.divider()
    today = datetime.date.today()
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

# --- 2. 核心执行逻辑 ---
if st.button("🚀 执行同步与归因分析", use_container_width=True):
    if not token:
        st.error("请输入有效的 API Token")
        st.stop()

    # 处理日期范围
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        temp_date = d_range[0] if isinstance(d_range, (list, tuple)) else d_range
        start_str = end_str = temp_date.strftime('%Y-%m-%d')

    with st.status("数据处理中...", expanded=True) as status:
        st.write("📝 正在构造归因 SQL...")
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        
        st.write("🌐 正在调取数数 API...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"API 调用失败: {error}")
            status.update(label="❌ 任务失败", state="error")
            st.stop()
            
        st.write("🧹 正在修复中文乱码并对齐表头...")
        df = clean_sql_response(raw_text)
        
        if df is None or df.empty:
            st.error("清洗后无有效数据。请检查原始快照。")
            status.update(label="❌ 任务失败", state="error")
            st.stop()
        
        status.update(label="✅ 分析完成", state="complete", expanded=False)

    # --- 3. 结果展示 ---
    st.divider()
    
    # 汇总计算
    total_cost = df['Cost'].sum()
    total_iap = df['IAP Revenue'].sum()
    total_ad = df['Ad Revenue'].sum()
    total_rev = total_iap + total_ad
    roi = (total_rev / total_cost) if total_cost > 0 else 0.0

    # 指标卡
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗 (Cost)", f"${total_cost:,.2f}")
    c2.metric("总营收 (IAP+Ad)", f"${total_rev:,.2f}")
    c3.metric("整体 ROI", f"{roi:.2%}")
    c4.metric("广告营收占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

    # 详情表格
    st.subheader("📋 投放归因明细")
    # 仅展示核心关注列
    display_cols = ['Date', 'Campaign Name', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
    # 过滤掉不存在的列（防御）
    actual_show = [c for c in display_cols if c in df.columns]
    st.dataframe(df[actual_show], use_container_width=True, hide_index=True)

    # 导出 CSV (使用 utf-8-sig 确保 Excel 打开中文正常)
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 下载完整归因报表 (CSV)", csv_data, f"ROI_Report_{start_str}.csv", "text/csv")
