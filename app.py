import streamlit as st
import pandas as pd
from ta_api import TADataClient
import urllib3

# 忽略安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="TA SQL 助手", layout="wide")

st.title("📊 数数科技 SQL 数据抽检")

with st.sidebar:
    st.header("配置")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("API 地址", value="https://ta-open.jackpotlandslots.com")

# 默认 SQL 示例 (请根据你的项目表名修改，如 v_event_46)
default_sql = """SELECT 
    "#event_name", 
    "#event_time", 
    "#user_id" 
FROM v_event_46 
WHERE "$part_date" = '2026-03-12' 
LIMIT 100"""

sql_input = st.text_area("输入 SQL 查询语句", value=default_sql, height=200)

if st.button("执行查询", use_container_width=True):
    if not token:
        st.error("请输入 Token")
    else:
        with st.status("正在执行 SQL 查询...", expanded=True) as status:
            client = TADataClient(api_url, token)
            result = client.query_sql(sql_input)
            
            if result["status"] == "success":
                df = result["data"]
                status.update(label=f"✅ 查询成功！共 {len(df)} 行数据", state="complete")
                
                st.subheader("数据明细")
                st.dataframe(df, use_container_width=True)
                
                # 下载按钮
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("下载 CSV 数据", csv, "ta_query_result.csv", "text/csv")
            else:
                st.error("❌ 查询失败")
                st.write(result["message"])
                status.update(label="发生错误", state="error")
