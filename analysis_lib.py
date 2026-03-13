class AdAnalysis:
    @staticmethod
    def get_absolute_summary_sql(project_id, start_date, end_date):
        """
        全量汇总 SQL：不分层级、不关联字典，确保数据 100% 完整。
        用于核对项目总账。
        """
        return f"""
/* sessionProperties: {"ignore_downstream_preferences":"true"} */
SELECT * FROM (
    SELECT 
        '全量汇总 (真值)' AS "Date",
        'Total' AS "Dimension Value",
        'All Channels' AS "Media Source",
        'All' AS "OS",
        SUM(cost_val) AS "Cost",
        SUM(plot_uv) AS "Plot UV",
        -- 填充空列以保持 clean_sql_response 兼容性
        0 AS "ECPM_Null", 0 AS "ECPM_0_100", 0 AS "ECPM_100_200", 
        0 AS "ECPM_200_300", 0 AS "ECPM_300_400", 0 AS "ECPM_400_500", 0 AS "ECPM_500+",
        0 AS "L10 UV", 0 AS "L20 UV", 0 AS "L30 UV", 0 AS "L40 UV", 0 AS "L50 UV",
        0 AS "L60 UV", 0 AS "L70 UV", 0 AS "L80 UV", 0 AS "L90 UV", 0 AS "L100 UV",
        SUM(iap_uv) AS "IAP UV",
        0 AS "IAP Times",
        SUM(iap_rev) AS "IAP Revenue",
        SUM(ad_uv) AS "Ad UV",
        SUM(ad_rev) AS "Ad Revenue",
        SUM(cost_val) AS "total_amount",
        1 AS "group_num_0",
        1 AS "group_num"
    FROM (
        -- 1. 原始消耗：直接读取，不挂载任何维度限制
        SELECT 
            CAST(cost AS DOUBLE) as cost_val,
            0 as plot_uv, 0 as iap_uv, 0 as iap_rev, 0 as ad_uv, 0 as ad_rev
        FROM v_event_{project_id}
        WHERE "$part_event" = 'appsflyer_master_data' 
          AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
        
        UNION ALL
        
        -- 2. 全量行为：统计这段时间内产生的全部转化和收入
        SELECT 
            0 as cost_val,
            COUNT(DISTINCT IF("$part_event" = 'first_finish_plot', "#user_id")) as plot_uv,
            COUNT(DISTINCT IF("$part_event" = 'iap_recharge_succeed', "#user_id")) as iap_uv,
            SUM(CAST(IF("$part_event" = 'iap_recharge_succeed', iap_product_currency) AS DOUBLE))/100*0.7 as iap_rev,
            COUNT(DISTINCT IF("$part_event" = 'applovin_ad_revenue_impression_level', "#user_id")) as ad_uv,
            SUM(CAST(IF("$part_event" = 'applovin_ad_revenue_impression_level' AND ad_format IN ('REWARDED','INTER'), revenue) AS DOUBLE)) as ad_rev
        FROM v_event_{project_id}
        WHERE "$part_event" IN ('first_finish_plot', 'iap_recharge_succeed', 'applovin_ad_revenue_impression_level')
          AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
    )
)
"""

    @staticmethod
    def get_advertising_report_sql(project_id, start_date, end_date, dimension="campaign_name"):
        """
        多维归因 SQL：基于 te_ads_object 字典进行匹配。
        """
        # 物理字段名映射
        field_mapping = {
            "campaign_name": "campaign_name",
            "adgroup_name": "ad_group_name", 
            "ad_name": "ad_name"
        }
        
        real_field = field_mapping.get(dimension, dimension)
        
        # 针对消耗数据（单表查询）
        dim_raw = f'"te_ads_object"."{real_field}"'
        # 针对用户行为数据（JOIN 查询）
        dim_with_u = f'u."te_ads_object"."{real_field}"'

        template = """
/* sessionProperties: {"ignore_downstream_preferences":"true"} */
SELECT * FROM (
    SELECT *,
        count("Cost") OVER () group_num_0,
        count(1) OVER () group_num 
    FROM (
        SELECT 
            format_datetime("$__Date_Time", 'yyyy-MM-dd') AS "Date",
            group_0 AS "Dimension Value",
            media_source AS "Media Source",
            array_join(array_distinct(all_os), ', ') AS "OS",
            internal_amount_0 AS "Cost", 
            internal_amount_1 AS "Plot UV", 
            internal_amount_16 AS "ECPM_Null",
            internal_amount_17 AS "ECPM_0_100",
            internal_amount_18 AS "ECPM_100_200",
            internal_amount_19 AS "ECPM_200_300",
            internal_amount_20 AS "ECPM_300_400",
            internal_amount_21 AS "ECPM_400_500",
            internal_amount_22 AS "ECPM_500+",
            internal_amount_2 AS "L10 UV", internal_amount_3 AS "L20 UV",
            internal_amount_8 AS "L30 UV", internal_amount_9 AS "L40 UV",
            internal_amount_10 AS "L50 UV", internal_amount_11 AS "L60 UV",
            internal_amount_12 AS "L70 UV", internal_amount_13 AS "L80 UV",
            internal_amount_14 AS "L90 UV", internal_amount_15 AS "L100 UV",
            internal_amount_6 AS "IAP UV", 
            internal_amount_23 AS "IAP Times", 
            CAST(coalesce(internal_amount_7, 0) AS DOUBLE)/100*0.7 AS "IAP Revenue",
            internal_amount_4 AS "Ad UV", 
            internal_amount_5 AS "Ad Revenue", 
            sum(IF(is_finite(internal_amount_0), internal_amount_0, 0)) OVER (PARTITION BY "$__Date_Time", group_0, media_source) as total_amount
        FROM (
            SELECT group_0, media_source, "$__Date_Time",
                arbitrary(internal_amount_0) internal_amount_0, arbitrary(internal_amount_1) internal_amount_1,
                arbitrary(internal_amount_2) internal_amount_2, arbitrary(internal_amount_3) internal_amount_3,
                arbitrary(internal_amount_4) internal_amount_4, arbitrary(internal_amount_5) internal_amount_5,
                arbitrary(internal_amount_6) internal_amount_6, arbitrary(internal_amount_7) internal_amount_7,
                arbitrary(internal_amount_8) internal_amount_8, arbitrary(internal_amount_9) internal_amount_9,
                arbitrary(internal_amount_10) internal_amount_10, arbitrary(internal_amount_11) internal_amount_11,
                arbitrary(internal_amount_12) internal_amount_12, arbitrary(internal_amount_13) internal_amount_13,
                arbitrary(internal_amount_14) internal_amount_14, arbitrary(internal_amount_15) internal_amount_15,
                arbitrary(internal_amount_16) internal_amount_16, arbitrary(internal_amount_17) internal_amount_17,
                arbitrary(internal_amount_18) internal_amount_18, arbitrary(internal_amount_19) internal_amount_19,
                arbitrary(internal_amount_20) internal_amount_20, arbitrary(internal_amount_21) internal_amount_21,
                arbitrary(internal_amount_22) internal_amount_22, arbitrary(internal_amount_23) internal_amount_23,
                array_agg(os_val) FILTER (WHERE os_val IS NOT NULL) as all_os
            FROM (
                -- 消耗数据
                SELECT 
                    CASE 
                        WHEN "te_ads_object" IS NULL THEN '自然量'
                        WHEN <<DIM_RAW>> IS NULL THEN '自然量'
                        ELSE <<DIM_RAW>> 
                    END AS group_0,
                    CASE 
                        WHEN "te_ads_object" IS NULL THEN 'Organic'
                        WHEN "te_ads_object"."media_source" IS NULL THEN 'Organic'
                        ELSE "te_ads_object"."media_source"
                    END AS media_source,
                    ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
                    CAST(coalesce(SUM(CAST(cost AS DOUBLE)), 0) AS DOUBLE) internal_amount_0,
                    NULL internal_amount_1, NULL internal_amount_2, NULL internal_amount_3, 
                    NULL internal_amount_4, NULL internal_amount_5, NULL internal_amount_6, NULL internal_amount_7,
                    NULL internal_amount_8, NULL internal_amount_9, NULL internal_amount_10, NULL internal_amount_11,
                    NULL internal_amount_12, NULL internal_amount_13, NULL internal_amount_14, NULL internal_amount_15,
                    NULL internal_amount_16, NULL internal_amount_17, NULL internal_amount_18, NULL internal_amount_19,
                    NULL internal_amount_20, NULL internal_amount_21, NULL internal_amount_22, NULL internal_amount_23,
                    NULL as os_val
                FROM v_event_<<PROJECT_ID>> 
                WHERE "$part_event" = 'appsflyer_master_data' 
                  AND "$part_date" BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
                GROUP BY 1, 2, 3
                
                UNION ALL
                
                -- 用户行为数据
                SELECT 
                    ta_u.group_0,
                    ta_u.media_source,
                    ta_date_trunc('day', ta_u.inst_t, 1) AS "$__Date_Time",
                    NULL internal_amount_0,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'first_finish_plot', ta_ev."#user_id"))) AS DOUBLE) internal_amount_1,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '10', ta_ev."#user_id"))) AS DOUBLE) internal_amount_2,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '20', ta_ev."#user_id"))) AS DOUBLE) internal_amount_3,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev."#user_id"))) AS DOUBLE) internal_amount_4,
                    CAST(SUM(CAST(IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev.revenue) AS DOUBLE)) AS DOUBLE) internal_amount_5,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev."#user_id"))) AS DOUBLE) internal_amount_6,
                    CAST(SUM(CAST(IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev.iap_product_currency) AS DOUBLE)) AS DOUBLE) internal_amount_7,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '30', ta_ev."#user_id"))) AS DOUBLE) internal_amount_8,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '40', ta_ev."#user_id"))) AS DOUBLE) internal_amount_9,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '50', ta_ev."#user_id"))) AS DOUBLE) internal_amount_10,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '60', ta_ev."#user_id"))) AS DOUBLE) internal_amount_11,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '70', ta_ev."#user_id"))) AS DOUBLE) internal_amount_12,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '80', ta_ev."#user_id"))) AS DOUBLE) internal_amount_13,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '90', ta_ev."#user_id"))) AS DOUBLE) internal_amount_14,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '100', ta_ev."#user_id"))) AS DOUBLE) internal_amount_15,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm IS NULL, ta_ev."#user_id"))) AS DOUBLE) internal_amount_16,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 0 AND ta_u.ecpm < 100, ta_ev."#user_id"))) AS DOUBLE) internal_amount_17,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 100 AND ta_u.ecpm < 200, ta_ev."#user_id"))) AS DOUBLE) internal_amount_18,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 200 AND ta_u.ecpm < 300, ta_ev."#user_id"))) AS DOUBLE) internal_amount_19,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 300 AND ta_u.ecpm < 400, ta_ev."#user_id"))) AS DOUBLE) internal_amount_20,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 400 AND ta_u.ecpm < 500, ta_ev."#user_id"))) AS DOUBLE) internal_amount_21,
                    CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 500, ta_ev."#user_id"))) AS DOUBLE) internal_amount_22,
                    CAST(COUNT(IF(ta_ev."$part_event" = 'iap_recharge_succeed', 1)) AS DOUBLE) internal_amount_23,
                    arbitrary(ta_u.os_val) as os_val
                FROM (
                    SELECT "#user_id", "$part_event", "level_id", "ad_format", "revenue", "iap_product_currency", "#app_version"
                    FROM v_event_<<PROJECT_ID>> 
                    WHERE "$part_event" IN ('first_finish_plot', 'level_start', 'applovin_ad_revenue_impression_level', 'iap_recharge_succeed')
                      AND "$part_date" BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
                ) ta_ev 
                INNER JOIN (
                    SELECT 
                        ev."#user_id", 
                        CASE 
                            WHEN u."te_ads_object" IS NULL THEN '自然量'
                            WHEN <<DIM_WITH_U>> IS NULL THEN '自然量'
                            ELSE <<DIM_WITH_U>> 
                        END AS group_0, 
                        CASE 
                            WHEN u."te_ads_object" IS NULL THEN 'Organic'
                            WHEN u."te_ads_object"."media_source" IS NULL THEN 'Organic'
                            ELSE u."te_ads_object"."media_source"
                        END AS media_source,
                        u."app_version_first" AS v_first,
                        min(ev."#event_time") AS inst_t, 
                        arbitrary(ev."#os") as os_val,
                        arbitrary(u.first_rv_ecpm) as ecpm
                    FROM v_event_<<PROJECT_ID>> ev
                    LEFT JOIN v_user_<<PROJECT_ID>> u ON ev."#user_id" = u."#user_id"
                    WHERE ev."$part_event" = 'first_finish_plot'
                      AND ev."$part_date" BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
                    GROUP BY 1, 2, 3, 4
                ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
                WHERE ta_ev."#app_version" = ta_u.v_first
                GROUP BY 1, 2, 3
            ) 
            WHERE "$__Date_Time" >= TIMESTAMP '<<START_DATE>>' AND "$__Date_Time" < date_add('day', 1, TIMESTAMP '<<END_DATE>>')
            GROUP BY group_0, media_source, "$__Date_Time"
        )
        WHERE (internal_amount_0 > 0 OR internal_amount_1 > 0)
    )
) 
ORDER BY "Date" DESC, total_amount DESC 
LIMIT 1000
"""
        sql = template.replace("<<PROJECT_ID>>", str(project_id))\
                      .replace("<<START_DATE>>", start_date)\
                      .replace("<<END_DATE>>", end_date)\
                      .replace("<<DIM_RAW>>", dim_raw)\
                      .replace("<<DIM_WITH_U>>", dim_with_u)
        return sql
