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
    # 允许选择时间范围
    d_range = st.date_input("分析周期", [today - datetime.timedelta(days=7), today])

# --- 2. 核心执行逻辑 ---
if st.button("🚀 执行同步与归因分析", use_container_width=True):
    if not token:
        st.error("请输入有效的 API Token")
        st.stop()

    # --- 修复日期对象报错逻辑 ---
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str = d_range[0].strftime('%Y-%m-%d')
        end_str = d_range[1].strftime('%Y-%m-%d')
    elif isinstance(d_range, (list, tuple)) and len(d_range) == 1:
        start_str = end_str = d_range[0].strftime('%Y-%m-%d')
    else:
        start_str = end_str = d_range.strftime('%Y-%m-%d')

    with st.status("正在启动自动化归因流...", expanded=True) as status:
        # A. 构建 SQL
        st.write(f"📝 正在生成 SQL ({start_str} 至 {end_str})...")
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        
        # B. 调用 API
        st.write("🌐 正在连接数数服务器...")
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"接口调用失败: {error}")
            status.update(label="❌ 任务失败", state="error")
            st.stop()

        # C. 原始快照回显
        with st.expander("🔍 原始响应快照 (用于核对字段名)"):
            if raw_text:
                st.code(raw_text[:800], language="text")
            else:
                st.warning("API 返回内容为空！")
            
        # D. 清洗数据
        st.write("🧹 正在清洗并标准化数据结构...")
        df = clean_sql_response(raw_text)
        
        if df is None or df.empty:
            st.warning("清洗后的表格为空，可能是该时间段内无 appsflyer 数据。")
            status.update(label="⚠️ 无数据", state="error")
            st.stop()

        # E. 强制列名位置对齐 (针对 API 不返回表头的情况)
        # 根据你 SQL SELECT 的顺序进行强制映射
        try:
            # 索引说明: 0:Date, 1:Campaign Name, 2:OS, 3:Cost ... 25:IAP Revenue, 27:Ad Revenue
            if 'Cost' not in df.columns and len(df.columns) > 3:
                df = df.rename(columns={df.columns[3]: 'Cost'})
            if 'IAP Revenue' not in df.columns and len(df.columns) > 25:
                df = df.rename(columns={df.columns[25]: 'IAP Revenue'})
            if 'Ad Revenue' not in df.columns and len(df.columns) > 27:
                df = df.rename(columns={df.columns[27]: 'Ad Revenue'})
            if 'Campaign Name' not in df.columns and len(df.columns) > 1:
                df = df.rename(columns={df.columns[1]: 'Campaign Name'})
        except Exception as e:
            st.warning(f"列名自动对齐时出现小偏差: {e}")

        # F. 最终类型校准
        for std_name in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if std_name in df.columns:
                df[std_name] = pd.to_numeric(df[std_name], errors='coerce').fillna(0.0)
            else:
                df[std_name] = 0.0

        status.update(label="✅ 处理完成", state="complete", expanded=False)

    # --- 3. 结果展示 ---
    st.divider()
    
    try:
        # 计算全局指标
        total_cost = df['Cost'].sum()
        total_iap = df['IAP Revenue'].sum()
        total_ad = df['Ad Revenue'].sum()
        total_rev = total_iap + total_ad
        roi = (total_rev / total_cost) if total_cost > 0 else 0.0

        # 指标卡展示
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总消耗 (Cost)", f"${total_cost:,.2f}")
        c2.metric("总营收 (IAP+Ad)", f"${total_rev:,.2f}")
        c3.metric("整体 ROI", f"{roi:.2%}")
        c4.metric("广告营收占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

        # 数据表格展示
        st.subheader("📋 投放归因明细")
        # 整理显示的列顺序
        pref_order = ['Date', 'Campaign Name', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
        actual_cols = [c for c in pref_order if c in df.columns]
        # 补全其他可能存在的 SQL 字段
        other_cols = [c for c in df.columns if c not in pref_order and not c.startswith('group_num') and c != 'total_amount']
        
        st.dataframe(df[actual_cols + other_cols], use_container_width=True, hide_index=True)

        # 下载 CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载明细报表", csv, "report.csv", "text/csv")

    except Exception as e:
        st.error(f"渲染报表时出错: {e}")
        st.write("实际检测到的列名:", df.columns.tolist())
        st.write("数据预览:", df.head(3))
