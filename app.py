import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统 - 多维修复版", layout="wide")
st.title("🎯 广告投放多维归因报表")

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
    # 映射回 SQL 字段名 (根据数数标准，adgroup 无下划线)
    dim_map = {
        "广告计划": "campaign_name", 
        "广告组": "adgroup_name", 
        "广告创意": "ad_name"
    }
    selected_dim = dim_map[dim_choice]

    st.divider()
    today = datetime.date.today()
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

if st.button("🚀 执行多维归因分析", use_container_width=True):
    if not token: st.error("请输入 API Token"); st.stop()

    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        dt = d_range[0] if isinstance(d_range, list) else d_range
        start_str = end_str = dt.strftime('%Y-%m-%d')

    with st.status(f"正在分析 {dim_choice} 层级...", expanded=True) as status:
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str, dimension=selected_dim)
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"SQL 语法或执行错误: {error}"); st.stop()

        df = clean_sql_response(raw_text)
        if df.empty: st.error("未找到匹配数据"); st.stop()
        
        status.update(label="✅ 分析完成", state="complete", expanded=False)

    st.divider()
    
    # 指标展示
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

    st.subheader(f"📋 {dim_choice} 明细 (渠道: Media Source)")
    core_cols = ['Date', 'Media Source', 'Dimension Value', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
    st.dataframe(df[[c for c in core_cols if c in df.columns]], use_container_width=True, hide_index=True)
