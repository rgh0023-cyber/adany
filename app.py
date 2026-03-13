import streamlit as st
import datetime
import pandas as pd
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis

st.set_page_config(page_title="投放 ROI 归因系统 - 乱码修复版", layout="wide")
st.title("🎯 归因报表 - 编码兼容模式")

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
        st.error("请输入 API Token"); st.stop()

    # 日期转换
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_str, end_str = d_range[0].strftime('%Y-%m-%d'), d_range[1].strftime('%Y-%m-%d')
    else:
        dt = d_range[0] if isinstance(d_range, list) else d_range
        start_str = end_str = dt.strftime('%Y-%m-%d')

    with st.status("正在进行深度解码...", expanded=True) as status:
        sql = AdAnalysis.get_advertising_report_sql(project_id, start_str, end_str)
        client = TAClient(api_url, token)
        raw_text, error = client.execute_query(sql)
        
        if error:
            st.error(f"API 失败: {error}"); st.stop()

        # --- 暴力修复乱码逻辑 ---
        # 很多时候 Python 接收到的是 latin-1 损坏的字符串，我们需要将其还原为字节再用 GBK 解码
        corrected_text = raw_text
        try:
            # 尝试修复常见的 GBK -> ISO-8859-1 转换错误
            corrected_text = raw_text.encode('latin-1').decode('gbk')
        except:
            try:
                # 尝试修复 UTF-8 -> ISO-8859-1 转换错误
                corrected_text = raw_text.encode('latin-1').decode('utf-8')
            except:
                # 如果都失败了，维持原样
                corrected_text = raw_text

        with st.expander("🔍 原始响应快照 (已尝试自动修复编码)"):
            st.code(corrected_text[:1000])

        df = clean_sql_response(corrected_text)
        
        if df.empty:
            st.error("无法解析数据。可能是解码后格式仍不正确。")
            st.stop()
        
        status.update(label="✅ 处理成功", state="complete", expanded=False)

    # --- 渲染展示 ---
    st.divider()
    total_cost = df['Cost'].sum()
    total_iap = df['IAP Revenue'].sum()
    total_ad = df['Ad Revenue'].sum()
    total_rev = total_iap + total_ad
    roi = (total_rev / total_cost) if total_cost > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总消耗", f"${total_cost:,.2f}")
    c2.metric("总营收", f"${total_rev:,.2f}")
    c3.metric("ROI", f"{roi:.2%}")
    c4.metric("广告占比", f"{(total_ad/total_rev):.1%}" if total_rev > 0 else "0%")

    st.subheader("📋 投放明细")
    core_cols = ['Date', 'Campaign Name', 'OS', 'Cost', 'IAP Revenue', 'Ad Revenue', 'Plot UV']
    available_cols = [c for c in core_cols if c in df.columns]
    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
