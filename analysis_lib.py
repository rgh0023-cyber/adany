class AdAnalysis:
    @staticmethod
    def get_level_start_sql(project_id, start_date, end_date):
        # 封装你提供的复杂 SQL，并参数化日期
        return f"""
        select * from (select *,count(data_map_0) over () group_num_0,count(1) over () group_num from (select map_agg(if(amount_0 is not null and is_finite(amount_0) , "$__Date_Time", null), amount_0) data_map_0,sum(if(is_finite(amount_0) and ("$__Date_Time" <> timestamp '1981-01-01'), amount_0, 0)) total_amount from (select *, internal_amount_0 amount_0 from (select "$__Date_Time",cast(coalesce(COUNT(DISTINCT ta_ev."#user_id"), 0) as double) internal_amount_0 from (select *, ta_date_trunc('day',"@vpc_tz_#event_time", 1) "$__Date_Time" from (SELECT * from (select *, if("$etz" is not null and "$etz">=-30 and "$etz"<=30, date_add('second', cast((-8-"$etz")*3600 as integer), "#event_time"), "#event_time") "@vpc_tz_#event_time" from (select *, if("$stz" = -100, "#zone_offset", "$stz") "$etz" from (select "#event_name" "#event_name","#event_time" "#event_time","#user_id" "#user_id","#zone_offset" "#zone_offset","$part_date" "$part_date","$part_event" "$part_event",-100 "$stz" from (select "#user_id", "#event_time" "#event_time","$part_event" "$part_event","#zone_offset" "#zone_offset","$part_date" "$part_date","#event_name" "#event_name" from v_event_{project_id} where "$part_event" in ('level_start'))))))) ta_ev where (( ( "$part_event" IN ( 'level_start' ) ) )) and (("$part_date" between '{start_date}' and '{end_date}') and ("@vpc_tz_#event_time" >= timestamp '{start_date}' and "@vpc_tz_#event_time" < date_add('day', 1, TIMESTAMP '{end_date}'))) group by "$__Date_Time")))) ORDER BY total_amount DESC limit 1000
        """

    @staticmethod
    def calculate_metrics(df):
        if df.empty: return {}
        return {
            "total": df['value'].sum(),
            "avg": df['value'].mean(),
            "max": df['value'].max()
        }
