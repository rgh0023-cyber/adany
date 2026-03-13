import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response, parse_ta_map_column
from analysis_lib import AdAnalysis

st.set_page_config(page_title="数据分析系统", layout="wide")

st.title("📊 广告投放数据看板")

with st.sidebar:
    st.header("配置")
    token = st.text_input("Token", type="password")
    api_url = st.text_input("API URL", value="https://ta-open.jackpotlandslots.com")
    project_id = 46
    d_range = st.date_input("日期范围", [datetime.date(2026, 3, 6), datetime.date(2026, 3, 12)])

if st.button("🚀 执行同步与清洗", use_container_width=True):
    with st.status("正在处理中...", expanded=True) as status:
        
        # 1. 构造
        st.write("1️⃣ 正在生成 SQL...")
        sql = AdAnalysis.get_level_start_sql(project_id, d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d'))
        
        # 2. 连接
        st.write("2️⃣ 正在请求 TA 接口...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"连接失败: {error}")
            status.update(label="❌ 连接出错", state="error")
            st.stop()
            
        # 3. 清洗
        st.write("3️⃣ 正在清洗 Map 字段数据...")
        raw_df = clean_sql_response(raw_text)
        # 这里的 'data_map_0' 必须与 SQL 里的别名一致
        clean_df = parse_ta_map_column(raw_df, 'data_map_0')
        
        if clean_df.empty:
            st.error("数据清洗结果为空！")
            st.info(f"原始响应片段: {raw_text[:100]}...")
            status.update(label="❌ 清洗失败", state="error")
            st.stop()
            
        # 4. 分析
        st.write("4️⃣ 正在计算业务指标...")
        stats = AdAnalysis.calculate_metrics(clean_df)
        
        status.update(label="✅ 处理全部完成", state="complete", expanded=False)

    # 展示结果
    m1, m2 = st.columns(2)
    m1.metric("查询时段总计", f"{int(stats['total']):,}")
    m2.metric("日均值", f"{int(stats['avg']):.2f}")
    
    st.line_chart(clean_df.set_index('date'))
    st.dataframe(clean_df, use_container_width=True)
