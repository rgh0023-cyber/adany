import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response, parse_ta_map_column
from analysis_lib import AdAnalysis

st.set_page_config(page_title="数数数据分析", layout="wide")

st.title("📊 广告投放数据看板 (模块化调试版)")

with st.sidebar:
    st.header("配置")
    token = st.text_input("Token", type="password")
    api_url = st.text_input("API URL", value="https://ta-open.jackpotlandslots.com")
    project_id = 46
    d_range = st.date_input("日期范围", [datetime.date(2026, 3, 6), datetime.date(2026, 3, 12)])

if st.button("🚀 执行同步与清洗", use_container_width=True):
    with st.status("正在启动自动化数据流...", expanded=True) as status:
        
        # 1. SQL 构建
        st.write("1️⃣ 正在生成参数化 SQL...")
        start_str = d_range[0].strftime('%Y-%m-%d')
        end_str = d_range[1].strftime('%Y-%m-%d')
        sql = AdAnalysis.get_level_start_sql(project_id, start_str, end_str)
        
        # 2. 接口请求
        st.write("2️⃣ 正在通过 API 请求数数原始数据...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"连接失败: {error}")
            status.update(label="❌ 接口请求失败", state="error")
            st.stop()
            
        # 3. 数据清洗 (关键点)
        st.write("3️⃣ 正在解析 CSV 结构...")
        raw_df = clean_sql_response(raw_text)
        
        st.write("4️⃣ 正在解析 Map 内部嵌套数据...")
        # 此时不再传递 'data_map_0'，内部会自动按位置取第一列
        clean_df = parse_ta_map_column(raw_df)
        
        if clean_df.empty:
            st.error("❌ 数据清洗结果为空！")
            st.write("【原始文本快照】:", raw_text[:200])
            status.update(label="❌ 数据处理中断", state="error")
            st.stop()
            
        # 4. 指标分析
        st.write("5️⃣ 正在计算业务分析指标...")
        stats = AdAnalysis.calculate_metrics(clean_df)
        
        status.update(label="✅ 任务全部完成", state="complete", expanded=False)

    # 看板展示
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("时段总活跃 (level_start)", f"{int(stats.get('total', 0)):,}")
    m2.metric("日均水平", f"{int(stats.get('avg', 0)):,}")
    m3.metric("统计天数", f"{len(clean_df)} 天")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.write("📅 每日详情")
        st.dataframe(clean_df, use_container_width=True, hide_index=True)
    with col_b:
        st.write("📈 趋势变化")
        st.line_chart(clean_df.set_index('date'))
