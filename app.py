import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统 - 多维模式", layout="wide")
st.title("🎯 广告投放多维归因报表")

# --- 1. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    
    st.divider()
    st.header("📊 归集维度")
    dim_choice = st.radio(
        "请选择统计层级：",
        ["广告计划", "广告组", "广告创意"],
        index=0
    )
    # 映射回 SQL 字段名
    dim_map = {"广告计划": "campaign_name", "广告组": "adgroup_name", "广告创意": "ad_name"}
    selected_dim = dim_map[dim_choice]

    st.divider()
    today = datetime.date.today()
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

# --- 2. 核心执行逻辑 ---
if st.button("🚀 执行同步与归因分析", use_container_width=True):
    if not token:
        st.error("请输入 API Token"); st.stop()

    # 日期转换
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        dt = d_range[0] if isinstance(d_range, list) else d_range
        start_str = end_str = dt.strftime('%Y-%m-%d')

    with st.status(f"正在按【{dim_choice}】维度归因...", expanded=True) as status:
        # SQL 与 API 调用 (传入动态维度)
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str, dimension=selected_dim)
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"API 失败: {error}"); st.stop()

        with st.expander("🔍 原始响应快照 (Raw Data)"):
            # 暴力尝试修复编码
            try:
                debug_text = raw_text.encode('latin-1').decode('gbk')
            except:
                debug_text = raw_text
            st.code(debug_text[:1000])

        # 清洗
        # 注意：我们在 data_processor 里的 expected_cols 也要同步增加 Media Source 列
        df = clean_sql_response(raw_text)
        
        if df.empty:
            st.error("无法解析数据。"); st.stop()
        
        status.update(label=f"✅ {dim_choice} 归因完成", state="complete", expanded=False)

    # --- 3. 结果展示 ---
    st.divider()
    
    # 指标计算 (由于 data_processor 会根据位置对齐，这里列名必须准确)
    # 我们之前的 data_processor 逻辑会自动将 internal_amount_0 映射为 Cost 等
    total_cost = df['Cost'].sum()
    total_iap = df['IAP Revenue'].sum()
    total_ad = df['Ad Revenue'].sum()
    total_rev = total_iap + total_ad
    roi = (total_rev / total_cost) if total_cost > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗", f"${total_cost:,.2f}")
    c2.metric("总营收", f"${total_rev:,.2f}")
    c3.metric("整体 ROI", f"{roi:.2%}")
    c4.metric("广告占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

    st.subheader(f"📋 {dim_choice} 维度明细")
    # 显示核心列，增加了 Media Source 和 Dimension Value
    core_cols = ['Date', 'Media Source', 'Dimension Value', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
    available_cols = [c for c in core_cols if c in df.columns]
    
    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)

    # 下载
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(f"📥 下载{dim_choice}报表", csv, f"{selected_dim}_report.csv", "text/csv")
