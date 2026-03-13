# --- 第一部分：分析部门视图 (上部) ---
st.header("📊 业务分析层 (Cohort Based)")

df_analysed = DataAnalyser.perform_business_analysis(df_raw)

if not df_analysed.empty:
    m = DataAnalyser.get_summary_metrics(df_analysed)
    
    # 顶部指标卡片
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("总消耗", f"${m['总消耗']:,.2f}")
    c2.metric("总营收", f"${m['总营收']:,.2f}")
    c3.metric("综合 ROI", f"{m['综合 ROI']:.2%}")
    c4.metric("总转化成本(Plot)", f"${m['总转化成本']:.2f}")
    c5.metric("IAP UV 总数", f"{int(m['IAP UV 总数']):,}")
    c6.metric("IAP 转化成本", f"${m['IAP 转化成本']:.2f}")

    # 核心分析表格
    st.subheader("渠道/时间维度穿透")
    
    # 选择关键列进行展示
    view_cols = [
        'Status', 'Date', 'Dimension Value', 'Cost', 'Total Revenue', 
        'ROI', 'CPA_Plot', 'IAP UV', 'CPP_Pay', 'HV_Rate', 'PUR'
    ]
    
    st.dataframe(
        df_analysed[view_cols].style
        .background_gradient(subset=['ROI'], cmap='RdYlGn', vmin=0, vmax=1.2)
        .format({
            'Cost': '${:,.2f}', 'Total Revenue': '${:,.2f}', 'ROI': '{:.2%}',
            'CPA_Plot': '${:.2f}', 'IAP UV': '{:,.0f}', 'CPP_Pay': '${:.2f}',
            'HV_Rate': '{:.1%}', 'PUR': '{:.2%}'
        }),
        use_container_width=True, hide_index=True
    )

    st.caption("注：总转化成本 = 总消耗 / Plot UV；IAP 转化成本 = 总消耗 / IAP UV。当前数据为 Cohort 累积数据。")
