import streamlit as st
import datetime
import os
import requests
import pandas as pd
import numpy as np
# 确保以下自定义模块在同一目录下
from ta_api import TAClient
from data_processor import clean_sql_response
from analysis_lib import AdAnalysis
from data_analyser import DataAnalyser

# --- AI 解读：从 txt 读取 prompt / 配置，按 OS 与维度汇总后调 SiliconFlow ---
def _load_prompt_txt():
    path = os.path.join(os.path.dirname(__file__), "ai_interpret_prompt.txt")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def _load_siliconflow_config():
    path = os.path.join(os.path.dirname(__file__), "siliconflow_config.txt")
    cfg = {"model": "", "base_url": "https://api.siliconflow.cn/v1", "max_tokens": 2000, "temperature": 0.7}
    if not os.path.isfile(path):
        return cfg
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k in cfg:
                    cfg[k] = v if k in ("model", "base_url") else (int(v) if k == "max_tokens" else float(v))
    return cfg

def _build_data_summary(df):
    """基于本次查询全量数据（不按筛选），按总体 / OS / 维度名汇总，供 AI 解读"""
    if df is None or df.empty:
        return "（无数据）"
    sum_cols = [c for c in ["Cost", "Total Revenue", "IAP Revenue", "Plot UV", "IAP UV", "L20 UV"] if c in df.columns]
    ecpm_cols = [c for c in ["ECPM_100_200", "ECPM_200_300", "ECPM_300_400", "ECPM_400_500", "ECPM_500+"] if c in df.columns]
    if sum_cols:
        sum_cols = sum_cols + ecpm_cols
    if not sum_cols:
        return "（无可汇总指标）"
    def add_derived(g):
        if "Cost" in g.columns and g["Cost"].sum():
            g = g.copy()
            g["ROI"] = g["Total Revenue"] / g["Cost"] if "Total Revenue" in g.columns else np.nan
            g["CPA_Plot"] = g["Cost"] / g["Plot UV"].replace(0, np.nan) if "Plot UV" in g.columns else np.nan
            if "L20 UV" in g.columns and "Plot UV" in g.columns:
                g["L20_Pass_Rate"] = g["L20 UV"] / g["Plot UV"].replace(0, np.nan)
            if ecpm_cols and "Plot UV" in g.columns:
                g["High_ECPM_Rate"] = g[ecpm_cols].sum(axis=1) / g["Plot UV"].replace(0, np.nan)
        return g
    def row_text(name, r):
        parts = [f"Cost={r.get('Cost', 0):.2f}", f"Total Revenue={r.get('Total Revenue', 0):.2f}"]
        if not pd.isna(r.get("ROI")): parts.append(f"ROI={r['ROI']:.2%}")
        parts.append(f"Plot UV={r.get('Plot UV', 0):.0f}"); parts.append(f"IAP UV={r.get('IAP UV', 0):.0f}")
        if not pd.isna(r.get("L20_Pass_Rate")): parts.append(f"L20通过率={r['L20_Pass_Rate']:.1%}")
        if not pd.isna(r.get("High_ECPM_Rate")): parts.append(f"高质量占比={r['High_ECPM_Rate']:.1%}")
        return name + "： " + "，".join(parts)
    lines = []
    total = df[sum_cols].sum()
    total["ROI"] = total["Total Revenue"] / total["Cost"] if total.get("Cost") else np.nan
    total["CPA_Plot"] = total["Cost"] / total["Plot UV"] if total.get("Plot UV") else np.nan
    total["L20_Pass_Rate"] = total["L20 UV"] / total["Plot UV"] if total.get("Plot UV") else np.nan
    if ecpm_cols and total.get("Plot UV"):
        total["High_ECPM_Rate"] = sum(total.get(c, 0) for c in ecpm_cols) / total["Plot UV"]
    lines.append("【总体】")
    lines.append(row_text("汇总", total))
    if "OS" in df.columns:
        by_os = df.groupby("OS", dropna=False)[sum_cols].sum()
        by_os = add_derived(by_os)
        lines.append("\n【按 OS】")
        for os_name, r in by_os.iterrows():
            lines.append(row_text(str(os_name), r))
    if "Dimension Value" in df.columns:
        by_dim = df.groupby("Dimension Value", dropna=False)[sum_cols].sum()
        by_dim = add_derived(by_dim)
        lines.append("\n【按维度名称】")
        for dim_name, r in by_dim.iterrows():
            lines.append(row_text(str(dim_name), r))
    return "\n".join(lines)

def _call_siliconflow(prompt_text, data_summary, api_key, config):
    """用 SiliconFlow 生成解读，返回助手回复文本或错误信息"""
    if not api_key or not config.get("model"):
        return None, "未配置 SiliconFlow API Key 或模型名（见 secrets 与 siliconflow_config.txt）"
    base = (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
    url = f"{base}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt_text + "\n\n以下是本次查询的数据汇总：\n" + data_summary}],
        "max_tokens": config.get("max_tokens", 2000),
        "temperature": config.get("temperature", 0.7),
    }
    try:
        r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        if r.status_code != 200:
            return None, f"API 返回 {r.status_code}: {r.text[:200]}"
        data = r.json()
        choice = (data.get("choices") or [None])[0]
        if not choice:
            return None, "API 未返回内容"
        msg = choice.get("message") or {}
        return (msg.get("content") or "").strip(), None
    except Exception as e:
        return None, str(e)

# 1. 页面基础配置
st.set_page_config(
    page_title="ROI 智能分析系统 (Cohort)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 登录：未登录只显示登录框，验证通过后再显示主界面 ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def _check_login(username, password):
    """从 Secrets 读取预期账号密码并校验（未配置则不允许登录）"""
    try:
        want_user = st.secrets.get("login_username", "")
        want_pass = st.secrets.get("login_password", "")
        if not want_user or not want_pass:
            return False
        return username == want_user and password == want_pass
    except Exception:
        return False

if not st.session_state["logged_in"]:
    st.title("ROI 智能分析系统 — 登录")
    with st.form("login_form"):
        login_user = st.text_input(
            "用户名",
            value=st.session_state.get("last_login_username", ""),
            key="login_username_input",
        )
        login_pass = st.text_input(
            "密码",
            type="password",
            value=st.session_state.get("last_login_password", ""),
            key="login_password_input",
        )
        submitted = st.form_submit_button("登录")
        if submitted:
            if _check_login(login_user, login_pass):
                st.session_state["logged_in"] = True
                st.session_state["last_login_username"] = login_user
                st.session_state["last_login_password"] = login_pass
                st.rerun()
            else:
                st.error("用户名或密码错误")
    st.stop()

# --- 移动端适配：小屏下优化侧边栏、字号与表格 ---
MOBILE_CSS = """
<style>
@media (max-width: 768px) {
    /* 主内容区减少左右边距，便于窄屏阅读 */
    [data-testid="stAppViewContainer"] { padding: 0.5rem; }
    /* 侧边栏在窄屏时更容易触控 */
    [data-testid="stSidebar"] { min-width: 260px; }
    [data-testid="stSidebar"] .stButton > button { width: 100%; }
    /* 指标卡片和按钮占满可用宽度 */
    [data-testid="stVerticalBlock"] > div [data-testid="stMetric"] { min-width: 0; }
    [data-testid="column"] { min-width: 0; }
    /* 表格横向滚动，避免撑破布局 */
    [data-testid="stDataFrame"] { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    /* 多选、输入等触控区域稍大 */
    .stMultiSelect, .stTextInput, .stNumberInput { font-size: 16px; }
}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# --- 2. 侧边栏配置 ---
def _get_token():
    """优先从 Streamlit Secrets 读取 Token，否则使用侧边栏输入"""
    try:
        token = st.secrets.get("ta_api_token", "")
        if token:
            return token
        ta = st.secrets.get("ta") or {}
        if isinstance(ta, dict):
            return ta.get("token", "")
    except (FileNotFoundError, AttributeError, TypeError):
        pass
    return ""

with st.sidebar:
    st.header("⚙️ 数据源配置")
    token_from_secrets = _get_token()
    if token_from_secrets:
        st.caption("✅ 已使用已配置的 TA API Token（来自 Secrets）")
        token = token_from_secrets
        token_override = st.text_input("TA API Token（留空则使用上方已配置）", type="password", help="临时覆盖时在此输入")
        if token_override:
            token = token_override
    else:
        token = st.text_input("TA API Token", type="password", help="请输入数数科技 API 调用令牌，或配置 .streamlit/secrets.toml")
    project_id = st.number_input("项目 ID", value=46)
    
    st.markdown("---")
    st.header("🔍 查询维度")
    dim_choice = st.radio(
        "选择统计维度", 
        ["全量汇总", "广告计划", "广告组", "广告创意"],
        index=0
    )
    
    st.markdown("---")
    st.header("📅 Cohort 周期")
    # 默认选择最近 7 天
    default_start = datetime.date.today() - datetime.timedelta(days=7)
    default_end = datetime.date.today()
    d_range = st.date_input("选择新增批次范围", [default_start, default_end])

    st.markdown("---")
    if st.button("退出登录", use_container_width=True):
        st.session_state["logged_in"] = False
        if "cohort_df_analysed" in st.session_state:
            del st.session_state["cohort_df_analysed"]
            del st.session_state["cohort_df_raw"]
            del st.session_state["cohort_start_s"]
            del st.session_state["cohort_end_s"]
            del st.session_state["cohort_dim_choice"]
        st.rerun()

# --- 3. 核心逻辑：点击查询时执行并写入 session_state，之后仅用筛选改展示 ---
if st.button("🚀 执行 Cohort 深度分析", use_container_width=True):
    if not token:
        st.warning("⚠️ 请先在侧边栏输入 API Token")
        st.stop()
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s
    client = TAClient("https://ta-open.jackpotlandslots.com", token)
    with st.spinner(f"正在分析 {start_s} 至 {end_s} 的新增批次数据..."):
        if dim_choice == "全量汇总":
            sql = AdAnalysis.get_absolute_summary_sql(project_id, start_s, end_s)
        else:
            sql = AdAnalysis.get_advertising_report_sql(project_id, start_s, end_s, dim_choice)
        raw_text, error = client.execute_query(sql)
        if error:
            st.error(f"❌ SQL 执行错误: {error}")
            st.stop()
        df_raw = clean_sql_response(raw_text)
    if df_raw.empty:
        st.info("📭 该范围内暂无新增用户数据")
        st.stop()
    df_analysed = DataAnalyser.perform_business_analysis(df_raw)
    st.session_state["cohort_df_raw"] = df_raw
    st.session_state["cohort_df_analysed"] = df_analysed
    st.session_state["cohort_start_s"] = start_s
    st.session_state["cohort_end_s"] = end_s
    st.session_state["cohort_dim_choice"] = dim_choice
    if "ai_interpret_result" in st.session_state:
        del st.session_state["ai_interpret_result"]

# 有缓存结果时：始终展示结果区（卡片、筛选只改表格，其他不动）
if "cohort_df_analysed" in st.session_state:
    df_raw = st.session_state["cohort_df_raw"]
    df_analysed = st.session_state["cohort_df_analysed"].copy()
    start_s = st.session_state["cohort_start_s"]
    end_s = st.session_state["cohort_end_s"]
    dim_choice = st.session_state["cohort_dim_choice"]
    # 展示前兜底：若分析层未产出高质量占比，则用原始列在展示前算一列
    if "High_ECPM_Rate" not in df_analysed.columns:
        ecpm_cols = ['ECPM_100_200', 'ECPM_200_300', 'ECPM_300_400', 'ECPM_400_500', 'ECPM_500+']
        if all(c in df_analysed.columns for c in ecpm_cols) and 'Plot UV' in df_analysed.columns:
            high_sum = sum(df_analysed[c] for c in ecpm_cols)
            df_analysed['High_ECPM_Rate'] = np.where(
                df_analysed['Plot UV'] == 0, np.nan,
                high_sum / df_analysed['Plot UV']
            )
            df_analysed['High_ECPM_Rate'] = df_analysed['High_ECPM_Rate'].replace([np.inf, -np.inf], np.nan)
    metrics = DataAnalyser.get_summary_metrics(df_analysed)

    st.header("📊 业务分析层 (Cohort Based)")
    st.caption(f"分析逻辑：锁定 {start_s} ~ {end_s} 新增用户，统计其从激活至今的累积价值")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("总消耗 (Cost)", f"${metrics['总消耗']:,.2f}")
    c2.metric("总营收 (Gross)", f"${metrics['总营收']:,.2f}")
    c3.metric("综合 ROI", f"{metrics['综合 ROI']:.2%}")
    c4.metric("总转化成本(CPA)", f"${metrics['总转化成本']:.2f}")
    c5.metric("IAP UV", f"{int(metrics['IAP UV 总数']):,}")
    c6.metric("IAP 转化成本", f"${metrics['IAP 转化成本']:.2f}")

    # AI 数据解读：基于本次查询全量数据（不考虑筛选），prompt 与 SiliconFlow 参数来自 txt
    st.subheader("🤖 AI 数据解读")
    try:
        api_key = st.secrets.get("siliconflow_api_key", "")
    except Exception:
        api_key = ""
    if st.button("生成解读", key="ai_interpret_btn"):
        prompt_text = _load_prompt_txt()
        if not prompt_text:
            st.warning("未找到 ai_interpret_prompt.txt，请在本项目根目录放置该文件并写入 prompt。")
        else:
            with st.spinner("正在调用 AI 生成解读…"):
                cfg = _load_siliconflow_config()
                summary = _build_data_summary(df_analysed)
                content, err = _call_siliconflow(prompt_text, summary, api_key, cfg)
                if err:
                    st.error("解读生成失败：" + err)
                else:
                    st.session_state["ai_interpret_result"] = content
    if st.session_state.get("ai_interpret_result"):
        st.markdown(st.session_state["ai_interpret_result"])

    st.subheader("维度穿透视图")
    view_cols_wanted = [
        'Date', 'OS', 'Dimension Value', 'Cost', 'High_ECPM_Rate', 'Total Revenue', 'IAP Revenue',
        'ROI', 'CPA_Plot', 'IAP UV', 'CPP_Pay', 'L20_Pass_Rate', 'CPA_L20', 'PUR'
    ]
    display_cols = [c for c in view_cols_wanted if c in df_analysed.columns]
    df_view = df_analysed.copy()
    if 'OS' in df_analysed.columns:
        options_os = sorted(df_analysed['OS'].dropna().astype(str).unique().tolist())
        selected_os = st.multiselect("筛选 OS", options=options_os, default=[], key="filter_os")
        if selected_os:
            df_view = df_view[df_view['OS'].astype(str).isin(selected_os)]
    if 'Dimension Value' in df_analysed.columns:
        options_dim = sorted(df_analysed['Dimension Value'].dropna().astype(str).unique().tolist())
        selected_dim = st.multiselect("筛选 维度名称", options=options_dim, default=[], key="filter_dim")
        if selected_dim:
            df_view = df_view[df_view['Dimension Value'].astype(str).isin(selected_dim)]
    display_cols = [c for c in view_cols_wanted if c in df_view.columns]
    rename_map = {
        'Dimension Value': '维度名称',
        'High_ECPM_Rate': '高质量占比',
        'CPA_Plot': '激活成本',
        'CPP_Pay': '付费成本',
        'L20_Pass_Rate': '20关通过率',
        'CPA_L20': '20关成本',
        'PUR': '付费率'
    }
    display_df = df_view[display_cols].rename(columns={k: v for k, v in rename_map.items() if k in display_cols})
    format_map = {
        'Cost': '${:,.2f}', '高质量占比': '{:.1%}', 'Total Revenue': '${:,.2f}', 'IAP Revenue': '${:,.2f}', 'ROI': '{:.2%}',
        '激活成本': '${:.2f}', 'IAP UV': '{:,.0f}', '付费成本': '${:.2f}',
        '20关通过率': '{:.2%}', '20关成本': '${:.2f}', '付费率': '{:.2%}'
    }
    st.dataframe(
        display_df.style.format({k: v for k, v in format_map.items() if k in display_df.columns}, na_rep=''),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    with st.expander("🔍 原始数据明细 (对账专用)", expanded=False):
        st.write("此处展示 SQL 返回的原始字段（含 ECPM 分布及 L 等级 UV）")
        st.dataframe(df_raw, use_container_width=True)
        csv = df_raw.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下载原始报表 (.csv)",
            data=csv,
            file_name=f"cohort_{dim_choice}_{start_s}_to_{end_s}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.info("👈 请在左侧侧边栏配置 Token 和 Cohort 周期，然后点击执行分析。")
    with st.expander("📚 指标定义说明"):
        st.write("""
        - **总转化成本 (CPA)**: `总消耗 / Plot UV` (获取每个激活用户的成本)
        - **IAP 转化成本 (CPP)**: `总消耗 / IAP UV` (获取每个付费用户的成本)
        - **ROI**: `(内购净营收 + 广告营收) / 总消耗`
        - **高价值率**: ECPM > 300 的用户占比
        """)
