import streamlit as st
import datetime
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统", layout="wide")

st.title("🎯 广告投放多维归因报表")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("接口地址", value="https://ta-open.jackpotlandslots.com")
    project_id = st.number_input("项目 ID", value=46)
    
    st.divider()
    today = datetime.date.today()
    # 允许选择时间范围
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

# --- 执行逻辑 ---
if st.button("🚀 执行同步与归因分析", use_container_width=True):
    if not token:
        st.error("请输入有效的 API Token")
        st.stop()

    with st.status("正在启动自动化归因流...", expanded=True) as status:
        # 1. 构建 SQL
        st.write("📝 正在生成多表 Join 归因 SQL...")
        start_str = d_range[0].strftime('%Y-%m-%d')
        end_str = d_range[1].strftime('%Y-%m-%d')
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        
        # 2. 调用 API
        st.write("🌐 正在连接数数服务器...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"接口调用失败: {error}")
            status.update(label="❌ 任务失败", state="error")
            st.stop()

        # 【调试步骤】展示原始响应前 500 个字符
        with st.expander("🔍 原始响应快照 (用于证明数据存在)"):
            if raw_text:
                st.code(raw_text[:500], language="text")
            else:
                st.warning("原始响应完全为空！")
            
        # 3. 清洗数据
        st.write("🧹 正在标准化 CSV 结构...")
        df = clean_sql_response(raw_text)
        
        if df.empty:
            st.warning("清洗后的 DataFrame 为空。")
            st.info("💡 请检查上面的【原始响应快照】。如果快照里只有表头没有数据，说明 SQL 条件未匹配。")
            status.update(label="⚠️ 无有效数据", state="error")
            st.stop()

        # 4. 字段核对
        cols = df.columns.tolist()
        required = ['Cost', 'IAP Revenue', 'Ad Revenue']
        missing = [c for c in required if c not in cols]
        
        if missing:
            st.error(f"字段缺失: {missing}")
            st.write("实际返回列:", cols)
            status.update(label="❌ 字段冲突", state="error")
            st.stop()

        status.update(label="✅ 归因分析完成", state="complete", expanded=False)

    # --- 结果展示 ---
    st.divider()
    
    total_cost = df['Cost'].sum()
    total_iap = df['IAP Revenue'].sum()
    total_ad = df['Ad Revenue'].sum()
    total_rev = total_iap + total_ad
    roi = (total_rev / total_cost) if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗 (Cost)", f"${total_cost:,.2f}")
    c2.metric("总营收 (IAP+Ad)", f"${total_rev:,.2f}")
    c3.metric("整体 ROI", f"{roi:.2%}")
    c4.metric("广告占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

    st.subheader("📋 投放明细")
    st.dataframe(df, use_container_width=True, hide_index=True)
