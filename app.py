import streamlit as st
import pandas as pd
import time
from ta_api import TADataClient

st.title("🚀 数数数据分析看板")

# 侧边栏配置
with st.sidebar:
    st.header("API 配置")
    token = st.text_input("输入 TA API Token", type="password")
    project_id = st.number_input("项目 ID", value=46)

# 查询参数（对应你提供的示例）
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

if st.button("开始执行抓取", use_container_width=True):
    if not token:
        st.error("❌ 请先在侧边栏输入 Token")
    else:
        # 使用 st.status 展示具体步骤
        with st.status("正在处理数据请求...", expanded=True) as status:
            
            # 步骤 1：初始化
            st.write("1. 初始化 API 客户端...")
            client = TADataClient("https://ta-open.jackpotlandslots.com", token)
            time.sleep(0.5) # 仅为了演示效果，实际可删除
            
            # 步骤 2：网络请求
            st.write("2. 正在连接数数科技服务器并发送查询语句...")
            try:
                raw_data = client.fetch_report_data(params)
                
                if raw_data:
                    # 步骤 3：数据解析
                    st.write("3. 接口响应成功，正在解析 JSON 数据...")
                    
                    # 这里的逻辑需要根据你实际拿到的 JSON 结构调整
                    # 如果返回的是 {'rows': [...]}
                    if "rows" in raw_data:
                        df = pd.DataFrame(raw_data["rows"])
                        st.write(f"4. 成功加载 {len(df)} 行数据。")
                        
                        status.update(label="✅ 数据抓取完成！", state="complete", expanded=False)
                        
                        # 展示数据
                        st.divider()
                        st.subheader("📊 查询结果")
                        st.dataframe(df, use_container_width=True)
                        st.download_button("下载为 CSV", df.to_csv(index=False), "ta_data.csv")
                    else:
                        st.write("⚠️ 接口返回格式异常，未找到 rows 字段。")
                        st.json(raw_data)
                        status.update(label="❌ 数据解析失败", state="error")
                else:
                    st.write("❌ 获取数据为空，请检查 Token 或 ProjectID。")
                    status.update(label="❌ 抓取终止", state="error")
                    
            except Exception as e:
                st.write(f"‼️ 发生错误: {str(e)}")
                status.update(label="❌ 运行出错", state="error")
