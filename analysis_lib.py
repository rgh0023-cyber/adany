class AdAnalysis:
    @staticmethod
    def get_level_start_sql(project_id, start_date, end_date):
        """生成查询 level_start 的复杂 SQL 模板"""
        # 这里放入你之前提供的那段长 SQL，并把硬编码的日期替换为变量
        sql = f"""
        /* SQL 逻辑省略，使用你提供的模板，将日期替换为 {start_date} 和 {end_date} */
        ... v_event_{project_id} ...
        """
        return sql

    @staticmethod
    def calculate_metrics(df):
        """计算核心指标：总和、均值、环比等"""
        if df.empty:
            return {}
        metrics = {
            "total": df['value'].sum(),
            "avg": df['value'].mean(),
            "max": df['value'].max(),
            "count": len(df)
        }
        return metrics
