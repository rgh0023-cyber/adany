import streamlit as st
from ta_api import TAClient
from data_processor import clean_sql_response, parse_ta_map_column
from analysis_lib import AdAnalysis

st.set_page_config(page_title="数据分析系统", layout="wide")

# 侧边栏
with st.sidebar:
    token = st.text_input("Token", type="password")
    api_url = st.text_input("URL", value="https://ta-open.jackpotlandslots.com")
    project_id = 46

st.title("🎮 游戏投放数据概览")

# 模拟一个默认 SQL（或从 AdAnalysis 获取）
sql = AdAnalysis.get_level_start_sql(project_id, "2026-03-05", "2026-03-13")

if st.button("同步最新数据", use_container_width=True):
    # 1. 连接
    client = TAClient(api_url, token)
    raw_text, error = client.execute_query(sql)
    
    if error:
        st.error(f"连接失败: {error}")
    else:
        # 2. 清洗
        raw_df = clean_sql_response(raw_text)
        clean_df = parse_ta_map_column(raw_df, 'data_map_0')
        
        if not clean_df.empty:
            # 3. 分析
            stats = AdAnalysis.calculate_metrics(clean_df)
            
            # 4. 展示
            c1, c2, c3 = st.columns(3)
            c1.metric("总触发次数", f"{int(stats['total']):,}")
            c2.metric("日均用户", f"{int(stats['avg']):,}")
            c3.metric("峰值", f"{int(stats['max']):,}")
            
            st.divider()
            col_left, col_right = st.columns([1, 2])
            col_left.dataframe(clean_df, use_container_width=True)
            col_right.line_chart(clean_df.set_index('date'))
