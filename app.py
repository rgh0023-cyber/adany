import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response, parse_ta_map_column
from analysis_lib import AdAnalysis

st.set_page_config(page_title="数数分析看板-模块化版", layout="wide")

# UI 设置
st.title("📊 广告数据自动化分析系统")

with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    
    st.divider()
    d_range = st.date_input("选择查询周期", [datetime.date(2026, 3, 6), datetime.date(2026, 3, 12)])

if st.button("🚀 开始同步并分析数据", use_container_width=True):
    if not token:
        st.error("请先配置 Token")
    else:
        # 使用状态容器展示每一个模块的工作进度
        with st.status("正在启动自动化数据流...", expanded=True) as status:
            
            # 步骤 1: 构建查询
            st.write("📝 正在根据参数生成 SQL 模板...")
            start_str = d_range[0].strftime('%Y-%m-%d')
            end_str = d_range[1].strftime('%Y-%m-%d')
            sql = AdAnalysis.get_level_start_sql(project_id, start_str, end_str)
            
            # 步骤 2: 网络连接
            st.write("🌐 正在连接数数 API 并执行 SQL...")
            client = TAClient(api_url, token)
            raw_text, error = client.execute_query(sql)
            
            if error:
                st.error(f"连接环节出错: {error}")
                status.update(label="❌ 连接失败", state="error")
                st.stop()
            
            # 步骤 3: 数据清洗
            st.write("🧹 正在解析 CSV 并清洗压缩的 Map 字段...")
            raw_df = clean_sql_response(raw_text)
            clean_df = parse_ta_map_column(raw_df, 'data_map_0')
            
            if clean_df.empty:
                st.warning("数据清洗后为空，请检查 SQL 是否有结果返回。")
                st.write("原始响应：", raw_text)
                status.update(label="⚠️ 无数据结果", state="error")
                st.stop()
            
            # 步骤 4: 业务分析
            st.write("📊 正在计算核心分析指标...")
            stats = AdAnalysis.calculate_metrics(clean_df)
            
            # 完成
            status.update(label="✅ 数据处理完成，正在渲染看板", state="complete", expanded=False)

        # --- 最终结果展示 ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("累计触发", f"{int(stats['total']):,}")
        c2.metric("日均用户", f"{int(stats['avg']):,}")
        c3.metric("单日峰值", f"{int(stats['max']):,}")
        
        col_left, col_right = st.columns([1, 2])
        with col_left:
            st.dataframe(clean_df, use_container_width=True, hide_index=True)
        with col_right:
            st.line_chart(clean_df.set_index('date'))
