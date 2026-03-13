import streamlit as st
import pandas as pd
from ta_api import TADataClient
import urllib3

# 禁用 https 安全警告（配合 verify=False）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="TA 数据分析", layout="wide")

st.title("🚀 广告投放数据抓取测试")

with st.sidebar:
    st.header("1. 接口配置")
    token = st.text_input("API Token", type="password", help="从数数后台数据API页面获取")
    project_id = st.number_input("项目 ID", value=46)
    api_url = st.text_input("API 地址", value="https://ta-open.jackpotlandslots.com")

# 预设你提供的 JSON 参数
params = {
    "eventView": {
        "endTime": "2026-03-12 23:59:59",
        "startTime": "2026-03-06 00:00:00",
        "timeParticleSize": "day"
    },
    "events": [{
        "analysis": "TRIG_USER_NUM",
        "eventName": "level_start",
        "projectId": project_id
    }],
    "projectId": project_id
}

if st.button("开始抓取数据", use_container_width=True):
    if not token:
        st.error("请先输入 Token")
    else:
        with st.status("正在执行 API 联调...", expanded=True) as status:
            st.write("📡 发起请求到数数服务器...")
            client = TADataClient(api_url, token)
            result = client.fetch_report_data(params)
            
            st.write(f"🌐 HTTP 状态码: {result['status_code']}")
            
            if result['status_code'] == 200:
                resp_json = result['data']
                if resp_json.get("code") == 0:
                    st.write("✅ 业务逻辑成功，正在渲染表格...")
                    # 尝试解析数数特有的 rows 数据结构
                    data_payload = resp_json.get("data", {})
                    if "rows" in data_payload:
                        df = pd.DataFrame(data_payload["rows"])
                        status.update(label="数据抓取成功", state="complete", expanded=False)
                        st.subheader("📊 数据结果预览")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("请求成功但未找到 rows 数据。")
                        st.json(resp_json)
                else:
                    st.error(f"❌ 数数报错 (code={resp_json.get('code')}): {resp_json.get('msg')}")
                    st.json(resp_json)
                    status.update(label="业务报错", state="error")
            else:
                st.error(f"🚨 请求失败 (HTTP {result['status_code']})")
                st.code(result['text'], language="html")
                status.update(label="连接失败", state="error")
