
import streamlit as st
import pandas as pd
from ta_api import TADataClient

st.title("数数数据 API 对接测试")

# 建议将 Token 放入 secrets
token = st.text_input("输入你的 TA API Token", type="password")

if st.button("开始抓取数据"):
    if not token:
        st.error("请输入 Token")
    else:
        client = TADataClient("https://ta-open.jackpotlandslots.com", token)
        
        # 定义请求参数（即你提供的示例）
        params = {
            "eventView": {
                "endTime": "2026-03-12 23:59:59",
                "startTime": "2026-03-06 00:00:00",
                "timeParticleSize": "day"
            },
            "events": [{
                "analysis": "TRIG_USER_NUM",
                "eventName": "level_start",
                "projectId": 46
            }],
            "projectId": 46
        }
        
        with st.spinner("正在请求数数后台..."):
            raw_data = client.fetch_report_data(params)
            
            if raw_data:
                st.success("数据获取成功！")
                
                # 数据处理逻辑：将 TA 返回的 rows 转为 DataFrame
                # 注意：具体解析逻辑需根据 raw_data 的实际层级结构调整
                if "rows" in raw_data:
                    df = pd.DataFrame(raw_data["rows"])
                    st.write("数据预览：")
                    st.dataframe(df)
                else:
                    st.write("原始返回数据：")
                    st.json(raw_data)
