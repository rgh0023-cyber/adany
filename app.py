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

    with st.status("正在启动自动化归因流...", expanded=True) as status:
        # A. 构建 SQL
        st.write("📝 正在生成 SQL...")
        # 兼容单选日期或日期范围
        if isinstance(d_range, list) and len(d_range) == 2:
            start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
        else:
            start_str = end_str = d_range.strftime('%Y-%m-%d')

        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        
        # B. 调用 API
        st.write("🌐 正在连接数数服务器...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"接口调用失败: {error}")
            status.update(label="❌ 任务失败", state="error")
            st.stop()

        # C. 原始快照回显 (证明数据已到达)
        with st.expander("🔍 原始响应快照 (Raw Data Snapshot)"):
            if raw_text:
                st.code(raw_text[:800], language="text")
            else:
                st.warning("API 返回内容为空！")
            
        # D. 清洗数据
        st.write("扫 正在清洗并标准化数据结构...")
        df = clean_sql_response(raw_text)
        
        if df is None or df.empty:
            st.warning("清洗后的 DataFrame 为空，请检查 SQL 逻辑或日期范围。")
            status.update(label="⚠️ 无数据", state="error")
            st.stop()

        # E. 动态对齐列名 (防御性处理)
        # 确保计算所需的列在 df 中存在，不存在则补 0，防止 sum() 报错
        for required_col in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if required_col not in df.columns:
                df[required_col] = 0.0
            else:
                # 再次确保是数值类型
                df[required_col] = pd.to_numeric(df[required_col], errors='coerce').fillna(0)

        status.update(label="✅ 处理完成", state="complete", expanded=False)

    # --- 3. 结果展示 ---
    st.divider()
    
    # 指标计算
    try:
        total_cost = float(df['Cost'].sum())
        total_iap = float(df['IAP Revenue'].sum())
        total_ad = float(df['Ad Revenue'].sum())
        total_rev = total_iap + total_ad
        roi = (total_rev / total_cost) if total_cost > 0 else 0.0

        # 顶部指标卡
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总消耗 (Cost)", f"${total_cost:,.2f}")
        c2.metric("总营收 (IAP+Ad)", f"${total_rev:,.2f}")
        c3.metric("整体 ROI", f"{roi:.2%}")
        c4.metric("广告营收占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

        # 详情表格
        st.subheader("📋 投放归因明细")
        # 整理列顺序，提升可读性
        display_cols = ['Date', 'Campaign Name', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
        actual_display = [c for c in display_cols if c in df.columns]
        st.dataframe(df[actual_display], use_container_width=True, hide_index=True)
        
        # 简单趋势图
        if 'Date' in df.columns and len(df) > 1:
            st.subheader("📈 日消耗与营收趋势")
            trend_df = df.groupby('Date')[['Cost', 'IAP Revenue', 'Ad Revenue']].sum()
            st.area_chart(trend_df)

    except Exception as e:
        st.error(f"报表渲染失败: {e}")
        st.write("当前 DataFrame 结构预览:", df.head())
        st.write("当前列名列表:", df.columns.tolist())

# 下载功能 (可选)
if 'df' in locals() and not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 下载完整报表 (CSV)",
        data=csv,
        file_name=f"roi_report_{start_str}.csv",
        mime="text/csv",
    )
