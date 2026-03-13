import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统 - 调试模式", layout="wide")
st.title("🎯 归因报表 - 原始数据排查")

# --- 1. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    st.divider()
    today = datetime.date.today()
    # 稍微拉长一点时间范围，确保能抓到有消耗的数据
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=14), today])

# --- 2. 核心执行逻辑 ---
if st.button("🔍 获取原始数据快照", use_container_width=True):
    if not token:
        st.error("请输入 API Token"); st.stop()

    # 处理日期
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        dt = d_range[0] if isinstance(d_range, list) else d_range
        start_str = end_str = dt.strftime('%Y-%m-%d')

    with st.status("正在抓取原始数据...", expanded=True) as status:
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        client = TAClient(api_url, token)
        
        # 直接拿原始 Response 对象，看看字节层面的内容
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"API 失败: {error}"); st.stop()

        status.update(label="✅ 数据已到达", state="complete")

    # --- 重点：全屏展示快照 ---
    st.subheader("🛠️ 原始响应数据 (前 2000 字符)")
    st.info("提示：请查看下方代码块中，第二列（即日期后的那一列）的内容。如果是乱码，通常看起来像 'ç¬¬ä¸' 这种字符。")
    
    # 使用 st.text 配合大容器，防止缩略显示
    st.text_area("Raw CSV Output", value=raw_text[:2000], height=400)

    # --- 尝试解析并显示表格 ---
    st.divider()
    st.subheader("📊 尝试解析后的表格预览")
    df = clean_sql_response(raw_text)
    
    if not df.empty:
        st.write("系统识别到的 Campaign Name 示例:", df['Campaign Name'].unique()[:5].tolist())
        st.dataframe(df.head(20), use_container_width=True)
    else:
        st.error("解析失败，DataFrame 为空。请检查上方快照格式。")
