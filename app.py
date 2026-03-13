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
    # 增加“全量汇总”选项
    dim_choice = st.radio("分析维度：", ["全量汇总", "广告计划", "广告组", "广告创意"])
    
    # 字段名映射（对应明细模式）
    dim_map = {
        "广告计划": "campaign_name", 
        "广告组": "adgroup_name", 
        "广告创意": "ad_name"
    }
    
    st.divider()
    d_range = st.date_input("分析周期", [
        datetime.date.today() - datetime.timedelta(days=7), 
        datetime.date.today()
    ])

# --- 2. 核心执行逻辑 ---
if st.button("🚀 执行多维分析", use_container_width=True):
    if not token: 
        st.error("请填写 Token")
        st.stop()
    
    # 处理日期
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s

    with st.spinner("正在获取数据..."):
        client = TAClient(api_url, token)
        
        # --- 分支逻辑：全量汇总 vs 归因明细 ---
        if dim_choice == "全量汇总":
            sql = AdAnalysis.get_absolute_summary_sql(project_id, start_s, end_s)
        else:
            # 这里的 dim_choice 会映射到具体的字段名给 SQL 模板
            sql = AdAnalysis.get_advertising_report_sql(project_id, start_s, end_s, dim_map[dim_choice])
        
        # 执行查询
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"SQL 报错: {error}")
            with st.expander("查看错误详情"):
                st.code(sql)
            st.stop()

        # 解析数据
        df = clean_sql_response(raw_text)

    # --- 3. 渲染展示 ---
    if not df.empty:
        st.success(f"已按 {dim_choice} 完成数据调取")
        
        # 通用指标计算
        total_cost = df['Cost'].sum()
        total_iap = df['IAP Revenue'].sum()
        total_ad = df['Ad Revenue'].sum()
        total_rev = total_iap + total_ad
        
        # 顶部看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("消耗", f"${total_cost:,.2f}")
        c2.metric("营收", f"${total_rev:,.2f}")
        c3.metric("ROI", f"{(total_rev/total_cost):.2%}" if total_cost > 0 else "0%")
        c4.metric("Plot UV", f"{int(df['Plot UV'].sum()):,}")

        # 数据明细表格
        st.divider()
        if dim_choice == "全量汇总":
            st.subheader("📊 项目大盘汇总 (100% 完整)")
            # 汇总模式下隐藏不必要的空列
            summary_display = ['Dimension Value', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
            st.dataframe(df[summary_display], use_container_width=True, hide_index=True)
        else:
            st.subheader(f"📑 {dim_choice} 归因明细")
            # 明细模式下显示重要列
            detail_display = ['Date', 'Media Source', 'Dimension Value', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
            st.dataframe(df[[c for c in detail_display if c in df.columns]], use_container_width=True, hide_index=True)
            
        # 提供下载
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载 CSV 数据", csv, f"ROI_Report_{dim_choice}_{start_s}.csv", "text/csv")
        
    else:
        st.warning("⚠️ 未匹配到任何数据，请检查：\n1. 日期范围内是否有消耗/转化\n2. 广告字典是否配置")
        if st.checkbox("查看调试 SQL"):
            st.code(sql)
