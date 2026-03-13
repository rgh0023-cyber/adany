# ... (API 调用逻辑)

        # D. 清洗数据
        df = clean_sql_response(raw_text)
        
        if df.empty:
            st.warning("数据清洗失败，返回了空表格。")
            st.stop()

        # 【核心改动】强制检查计算列。如果还是没有，可能是列数对不上
        for col in ['Cost', 'IAP Revenue', 'Ad Revenue']:
            if col not in df.columns:
                # 尝试根据 SQL 的原始位置来找（假设 Cost 是第 4 列）
                # 注意：Python 索引从 0 开始，SQL 中 Date(0), Campaign(1), OS(2), Cost(3)
                try:
                    if col == 'Cost': df = df.rename(columns={df.columns[3]: 'Cost'})
                    if col == 'IAP Revenue': df = df.rename(columns={df.columns[25]: 'IAP Revenue'})
                    if col == 'Ad Revenue': df = df.rename(columns={df.columns[27]: 'Ad Revenue'})
                except:
                    df[col] = 0.0

        status.update(label="✅ 处理完成", state="complete", expanded=False)
