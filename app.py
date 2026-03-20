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

# Cohort 细粒度 SQL 返回后，按侧边栏「归集维度」做 sum 聚合（UV/金额类指标可累加至上一层级）
COHORT_SUM_COLS = [
    "Cost", "Plot UV", "ECPM_Null", "ECPM_0_100", "ECPM_100_200", "ECPM_200_300", "ECPM_300_400", "ECPM_400_500", "ECPM_500+",
    "L10 UV", "L20 UV", "L30 UV", "L40 UV", "L50 UV", "L60 UV", "L70 UV", "L80 UV", "L90 UV", "L100 UV",
    "IAP UV", "IAP_UV_D0", "IAP Times", "IAP Revenue", "Ad UV", "Ad Revenue", "total_amount",
]

_LABEL_COHORT_ALL = "（全部）"


def aggregate_cohort_by_dim_choice(df, dim_choice):
    """
    四级：全部 → 广告计划 → 广告组 → 广告创意。
    归集在上一层时，下方层级在结果中置空；本层及以上层级有值（全部为固定标签）。
    """
    if df is None or df.empty:
        return df
    d = df.copy()
    sum_cols = [c for c in COHORT_SUM_COLS if c in d.columns]
    for c in sum_cols:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    col_plan, col_grp, col_cre = "维度名称_广告计划", "维度名称_广告组", "维度名称_广告创意"
    for c in (col_plan, col_grp, col_cre, "维度名称_全部"):
        if c not in d.columns:
            d[c] = ""
    level_map = {"全量汇总": 0, "广告计划": 1, "广告组": 2, "广告创意": 3}
    level = level_map.get(dim_choice, 0)
    if not sum_cols:
        return d

    def _norm_key(series):
        return series.fillna("").astype(str)

    if level == 0:
        d = d.copy()
        d["Date"] = _norm_key(d["Date"])
        d["OS"] = _norm_key(d["OS"])
        g = d.groupby(["Date", "OS"], as_index=False)[sum_cols].sum()
        g["Media Source"] = ""
        g["维度名称_全部"] = _LABEL_COHORT_ALL
        g[col_plan] = ""
        g[col_grp] = ""
        g[col_cre] = ""
        g["Dimension Value"] = _LABEL_COHORT_ALL
    elif level == 1:
        keys = ["Date", "OS", "Media Source", col_plan]
        d = d.copy()
        d["Date"] = _norm_key(d["Date"])
        d["OS"] = _norm_key(d["OS"])
        d["Media Source"] = _norm_key(d["Media Source"])
        d[col_plan] = _norm_key(d[col_plan])
        g = d.groupby(keys, as_index=False)[sum_cols].sum()
        g["维度名称_全部"] = _LABEL_COHORT_ALL
        g[col_grp] = ""
        g[col_cre] = ""
        g["Dimension Value"] = g[col_plan].astype(str)
    elif level == 2:
        keys = ["Date", "OS", "Media Source", col_plan, col_grp]
        d = d.copy()
        d["Date"] = _norm_key(d["Date"])
        d["OS"] = _norm_key(d["OS"])
        d["Media Source"] = _norm_key(d["Media Source"])
        d[col_plan] = _norm_key(d[col_plan])
        d[col_grp] = _norm_key(d[col_grp])
        g = d.groupby(keys, as_index=False)[sum_cols].sum()
        g["维度名称_全部"] = _LABEL_COHORT_ALL
        g[col_cre] = ""
        g["Dimension Value"] = g[col_grp].astype(str)
    else:
        g = d.copy()
        g["维度名称_全部"] = _LABEL_COHORT_ALL
        g["Dimension Value"] = g[col_cre].astype(str) if col_cre in g.columns else ""

    for c in ("group_num_0", "group_num"):
        if c in g.columns:
            g.drop(columns=[c], inplace=True, errors="ignore")
    return g


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
    sum_cols = [c for c in ["Cost", "Total Revenue", "IAP Revenue", "Plot UV", "IAP UV", "IAP_UV_D0", "L20 UV"] if c in df.columns]
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
        if "IAP_UV_D0" in r.index: parts.append(f"IAP_UV_D0={r.get('IAP_UV_D0', 0):.0f}")
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

# 追问时强制限定在数据解读范围的系统说明（会加入每次请求）
_AI_SCOPE_SYSTEM = "你是一位投放数据分析师。你的所有回答（包括首次解读与后续追问）必须严格限定在用户提供的本次查询数据解读范围内，仅基于已给数据作答，不要脱离数据编造或泛化。"

def _call_siliconflow_chat(api_key, config, messages):
    """用 SiliconFlow 多轮对话，messages 为 [{"role":"user"|"assistant"|"system", "content":"..."}, ...]，返回助手回复文本或错误信息"""
    if not api_key or not config.get("model"):
        return None, "未配置 SiliconFlow API Key 或模型名（见 secrets 与 siliconflow_config.txt）"
    base = (config.get("base_url") or "https://api.siliconflow.cn/v1").rstrip("/")
    url = f"{base}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": messages,
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
        st.rerun()

# --- 3. 核心逻辑：点击查询时覆盖当前结果；筛选仅作用于当前结果 ---
if st.button("🚀 执行 Cohort 深度分析", use_container_width=True):
    if not token:
        st.warning("⚠️ 请先在侧边栏输入 API Token")
        st.stop()
    start_s = d_range[0].strftime('%Y-%m-%d')
    end_s = d_range[1].strftime('%Y-%m-%d') if len(d_range) > 1 else start_s
    client = TAClient("https://ta-open.jackpotlandslots.com", token)
    with st.spinner(f"正在分析 {start_s} 至 {end_s} 的新增批次数据..."):
        # 全量/广告共用同一细粒度 SQL；归集维度仅在应用层聚合与展示层级
        sql = AdAnalysis.get_cohort_fine_grain_sql(project_id, start_s, end_s)
        raw_text, error = client.execute_query(sql)
        if error:
            st.error(f"❌ SQL 执行错误: {error}")
            st.stop()
        df_raw_detail = clean_sql_response(raw_text)
    if df_raw_detail.empty:
        st.info("📭 该范围内暂无新增用户数据")
        st.stop()
    df_agg = aggregate_cohort_by_dim_choice(df_raw_detail, dim_choice)
    df_analysed = DataAnalyser.perform_business_analysis(df_agg)
    # 覆盖当前查询结果：原始明细为细粒度；分析表为当前归集维度
    st.session_state["cohort_df_raw"] = df_raw_detail
    st.session_state["cohort_df_analysed"] = df_analysed
    st.session_state["cohort_start_s"] = start_s
    st.session_state["cohort_end_s"] = end_s
    st.session_state["cohort_dim_choice"] = dim_choice
    # 每次重查时清空 AI 对话，避免对话基于旧数据
    if "ai_interpret_conversation" in st.session_state:
        del st.session_state["ai_interpret_conversation"]

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

    # AI 数据解读：基于本次查询全量数据（不考虑筛选）；支持最多 2 次追问，回答限定在数据解读范围
    st.subheader("🤖 AI 数据解读")
    try:
        api_key = st.secrets.get("siliconflow_api_key", "")
    except Exception:
        api_key = ""
    conv = st.session_state.get("ai_interpret_conversation", [])

    if st.button("生成解读", key="ai_interpret_btn"):
        prompt_text = _load_prompt_txt()
        if not prompt_text:
            st.warning("未找到 ai_interpret_prompt.txt，请在本项目根目录放置该文件并写入 prompt。")
        else:
            with st.spinner("正在调用 AI 生成解读…"):
                cfg = _load_siliconflow_config()
                summary = _build_data_summary(df_analysed)
                user_content = prompt_text + "\n\n以下是本次查询的数据汇总：\n" + summary + "\n\n请根据以上数据给出总体解读。"
                messages = [
                    {"role": "system", "content": _AI_SCOPE_SYSTEM},
                    {"role": "user", "content": user_content},
                ]
                content, err = _call_siliconflow_chat(api_key, cfg, messages)
                if err:
                    st.error("解读生成失败：" + err)
                else:
                    st.session_state["ai_interpret_conversation"] = [
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": content},
                    ]
        st.rerun()

    # 展示已有对话：首次解读 + 追问与回答（不展示首条长 prompt）
    if conv:
        first_reply_shown = False
        for m in conv:
            if m["role"] == "assistant":
                st.markdown("**解读：**" if not first_reply_shown else "**答：**")
                st.markdown(m["content"])
                first_reply_shown = True
            else:
                if first_reply_shown:
                    st.markdown("**问：** " + m["content"])
        # 追问：每轮查询最多 2 个问题（不含首次“生成解读”）
        user_msgs = [m for m in conv if m["role"] == "user"]
        question_count = len(user_msgs) - 1
        can_ask = question_count < 2
        if can_ask:
            with st.form("ai_followup_form"):
                followup_q = st.text_input("追问（限定在本次数据解读范围内）", key="ai_followup_input")
                submitted = st.form_submit_button("提问")
                if submitted and followup_q.strip():
                    with st.spinner("正在生成回答…"):
                        cfg = _load_siliconflow_config()
                        new_conv = conv + [{"role": "user", "content": followup_q.strip()}]
                        messages = [{"role": "system", "content": _AI_SCOPE_SYSTEM}] + new_conv
                        content, err = _call_siliconflow_chat(api_key, cfg, messages)
                        if err:
                            st.error("追问回答失败：" + err)
                        else:
                            st.session_state["ai_interpret_conversation"] = new_conv + [{"role": "assistant", "content": content}]
                    st.rerun()
        else:
            st.caption("本轮已达 2 次追问上限，重新执行查询后可再次生成解读并追问。")

    st.subheader("维度穿透视图")
    st.caption(
        f"当前归集维度：**{dim_choice}** — 展示「（全部）」及本层以上层级；更细层级留空。"
    )
    view_cols_wanted = [
        'Date', 'OS', 'Media Source',
        '维度名称_全部', '维度名称_广告计划', '维度名称_广告组', '维度名称_广告创意',
        'Plot UV', 'Cost', 'High_ECPM_Rate', 'Total Revenue', 'IAP Revenue',
        'ROI', 'CPA_Plot', 'IAP UV', 'IAP_UV_D0', 'CPP_Pay', 'L20_Pass_Rate', 'CPA_L20', 'PUR',
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
        'Media Source': '媒体源',
        '维度名称_全部': '全部',
        '维度名称_广告计划': '广告计划',
        '维度名称_广告组': '广告组',
        '维度名称_广告创意': '广告创意',
        'Plot UV': '激活人数',
        'High_ECPM_Rate': '高质量占比',
        'CPA_Plot': '激活成本',
        'CPP_Pay': '付费成本',
        'L20_Pass_Rate': '20关通过率',
        'CPA_L20': '20关成本',
        'PUR': '付费率',
        'IAP_UV_D0': 'D0首充UV'
    }
    display_df = df_view[display_cols].rename(columns={k: v for k, v in rename_map.items() if k in display_cols})
    format_map = {
        'Cost': '${:,.2f}', '激活人数': '{:,.0f}', '高质量占比': '{:.1%}', 'Total Revenue': '${:,.2f}', 'IAP Revenue': '${:,.2f}',         'ROI': '{:.2%}',
        '激活成本': '${:.2f}', 'IAP UV': '{:,.0f}', 'D0首充UV': '{:,.0f}', '付费成本': '${:.2f}',
        '20关通过率': '{:.2%}', '20关成本': '${:.2f}', '付费率': '{:.2%}'
    }
    st.dataframe(
        display_df.style.format({k: v for k, v in format_map.items() if k in display_df.columns}, na_rep=''),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    with st.expander("🔍 原始数据明细 (对账专用)", expanded=False):
        st.caption("以下筛选 **独立于** 上方「维度穿透视图」；未选时表示不过滤。数据来自本次查询缓存，不会重新请求 API。")
        st.write("此处展示 SQL 返回的原始字段（含 ECPM 分布及 L 等级 UV）")
        df_src = df_raw.copy()
        raw_selected_os, raw_selected_dim = [], []
        if "OS" in df_src.columns:
            raw_options_os = sorted(df_src["OS"].dropna().astype(str).unique().tolist())
            raw_selected_os = st.multiselect("筛选 OS（原始表）", options=raw_options_os, default=[], key="filter_raw_os")
        if "Dimension Value" in df_src.columns:
            raw_options_dim = sorted(df_src["Dimension Value"].dropna().astype(str).unique().tolist())
            raw_selected_dim = st.multiselect("筛选 维度名称（原始表）", options=raw_options_dim, default=[], key="filter_raw_dim")
        df_raw_display = df_src.copy()
        if raw_selected_os and "OS" in df_raw_display.columns:
            df_raw_display = df_raw_display[df_raw_display["OS"].astype(str).isin(raw_selected_os)]
        if raw_selected_dim and "Dimension Value" in df_raw_display.columns:
            df_raw_display = df_raw_display[df_raw_display["Dimension Value"].astype(str).isin(raw_selected_dim)]
        st.dataframe(df_raw_display, use_container_width=True)
        csv = df_raw_display.to_csv(index=False).encode("utf-8")
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
