import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统", layout="wide")
st.title("🎯 广告投放多维归因报表")

with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    st.divider()
    today = datetime.date.today()
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

if st.button("🚀 执行同步与归因分析", use_container_width=True):
    if not token:
        st.error("请输入 Token"); st.stop()

    # 日期解析逻辑
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        start_str = end_str = (d_range[0] if isinstance(d_range, list) else d_range).strftime('%Y-%m-%d')

    with st.status("正在处理...", expanded=True) as status:
        st.write("📝 生成 SQL..."); sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        st.write("🌐 请求 API..."); client = TAClient(api_url, token); raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"API错误: {error}"); status.update(label="❌ 失败", state="error"); st.stop()
        
        with st.expander("🔍 原始响应快照"):
            st.code(raw_text[:500])

        st.write("🧹 清洗数据..."); df = clean_sql_response(raw_text)
        
        if df.empty:
            st.error("清洗结果为空。请确认快照里是否包含实际业务行。")
            status.update(label="❌ 无数据", state="error"); st.stop()
        
        status.update(label="✅ 完成", state="complete", expanded=False)

    # 渲染报表
    st.divider()
    total_cost = df['Cost'].sum(); total_iap = df['IAP Revenue'].sum(); total_ad = df['Ad Revenue'].sum()
    total_rev = total_iap + total_ad; roi = total_rev/total_cost if total_cost>0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗", f"${total_cost:,.2f}"); c2.metric("总营收", f"${total_rev:,.2f}")
    c3.metric("ROI", f"{roi:.2%}"); c4.metric("广告占比", f"{(total_ad/total_rev):.1%}" if total_rev>0 else "0%")
    
    st.subheader("📋 归因明细")
    cols = ['Date', 'Campaign Name', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
