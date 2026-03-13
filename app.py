import streamlit as st
import pandas as pd
from ta_api import TADataClient
import urllib3
import json

# 忽略安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="TA 报表 SQL 调试", layout="wide")

st.title("📊 复杂报表 SQL 穿透测试")

with st.sidebar:
    st.header("1. 接口凭证")
    token = st.text_input("API Token", type="password")
    api_url = st.text_input("API 地址", value="https://ta-open.jackpotlandslots.com")

# 预设你提供的这段复杂 SQL
complex_sql = """select * from (select *,count(data_map_0) over () group_num_0,count(1) over () group_num from (select map_agg(if(amount_0 is not null and is_finite(amount_0) , "$__Date_Time", null), amount_0) data_map_0,sum(if(is_finite(amount_0) and ("$__Date_Time" <> timestamp '1981-01-01'), amount_0, 0)) total_amount from (select *, internal_amount_0 amount_0 from (select "$__Date_Time",cast(coalesce(COUNT(DISTINCT ta_ev."#user_id"), 0) as double) internal_amount_0 from (select *, ta_date_trunc('day',"@vpc_tz_#event_time", 1) "$__Date_Time" from (SELECT * from (select *, if("$etz" is not null and "$etz">=-30 and "$etz"<=30, date_add('second', cast((-8-"$etz")*3600 as integer), "#event_time"), "#event_time") "@vpc_tz_#event_time" from (select *, if("$stz" = -100, "#zone_offset", "$stz") "$etz" from (select "#event_name" "#event_name","#event_time" "#event_time","#user_id" "#user_id","#zone_offset" "#zone_offset","$part_date" "$part_date","$part_event" "$part_event",-100 "$stz" from (select "#user_id", "#event_time" "#event_time","$part_event" "$part_event","#zone_offset" "#zone_offset","$part_date" "$part_date","#event_name" "#event_name" from v_event_46 where "$part_event" in ('level_start'))))))) ta_ev where (( ( "$part_event" IN ( 'level_start' ) ) )) and (("$part_date" between '2026-03-05' and '2026-03-13') and ("@vpc_tz_#event_time" >= timestamp '2026-03-06' and "@vpc_tz_#event_time" < date_add('day', 1, TIMESTAMP '2026-03-12'))) group by "$__Date_Time")))) ORDER BY total_amount DESC limit 1000"""

st.subheader("SQL 编辑区")
sql_query = st.text_area("SQL 语句", value=complex_sql, height=300)

if st.button("🚀 执行并分析数据", use_container_width=True):
    if not token:
        st.error("请在侧边栏配置 Token")
    else:
        with st.status("正在进行深度数据查询...", expanded=True) as status:
            client = TADataClient(api_url, token)
            result = client.query_sql(sql_query)
            
            if result["status"] == "success":
                df = result["data"]
                status.update(label="✅ 数据获取成功！", state="complete")
                
                # 数据预处理：这段 SQL 的结果通常只有一行，核心数据在 data_map_0
                st.subheader("📊 查询结果预览")
                st.dataframe(df)
                
                # 尝试解析 data_map_0 (Map 类型转为可视化表格)
                if 'data_map_0' in df.columns:
                    st.divider()
                    st.subheader("📈 趋势拆解")
                    try:
                        # 转换形如 {k1=v1, k2=v2} 的字符串为 DataFrame
                        map_str = df['data_map_0'].iloc[0]
                        # 简单清理：去掉 {} 并按逗号分割
                        items = map_str.strip("{}").split(", ")
                        map_data = [item.split("=") for item in items]
                        trend_df = pd.DataFrame(map_data, columns=['日期', '数值'])
                        trend_df['数值'] = pd.to_numeric(trend_df['数值'])
                        trend_df = trend_df.sort_values('日期')
                        
                        col1, col2 = st.columns([1, 2])
                        col1.table(trend_df)
                        col2.line_chart(trend_df.set_index('日期'))
                    except Exception as e:
                        st.info("数据格式较为复杂，已提供原始表格。")
            else:
                st.error("❌ 查询失败")
                st.json(result["message"])
                status.update(label="查询报错", state="error")
