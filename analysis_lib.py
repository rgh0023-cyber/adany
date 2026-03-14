import datetime

class AdAnalysis:
    @staticmethod
    def get_absolute_summary_sql(project_id, start_date, end_date):
        """
        全量汇总 SQL (Cohort 模式)：
        - 消耗端：通过 app_id 硬编码判定 (6748138347 为 iOS)
        - 行为端：通过日志原生 #os 判定
        """
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        return f"""
/* sessionProperties: {{"ignore_downstream_preferences":"true"}} */
SELECT * FROM (
    SELECT 
        format_datetime("$__Date_Time", 'yyyy-MM-dd') AS "Date",
        'Total' AS "Dimension Value",
        CAST(NULL AS VARCHAR) AS "Media Source",
        "OS",
        SUM(c0) AS "Cost", SUM(c1) AS "Plot UV", 
        SUM(c16) AS "ECPM_Null", SUM(c17) AS "ECPM_0_100", SUM(c18) AS "ECPM_100_200",
        SUM(c19) AS "ECPM_200_300", SUM(c20) AS "ECPM_300_400", SUM(c21) AS "ECPM_400_500", SUM(c22) AS "ECPM_500+",
        SUM(c2) AS "L10 UV", SUM(c3) AS "L20 UV", SUM(c8) AS "L30 UV", SUM(c9) AS "L40 UV", 
        SUM(c10) AS "L50 UV", SUM(c11) AS "L60 UV", SUM(c12) AS "L70 UV", SUM(c13) AS "L80 UV", 
        SUM(c14) AS "L90 UV", SUM(c15) AS "L100 UV",
        SUM(c6) AS "IAP UV", SUM(c23) AS "IAP Times", SUM(c7)/100*0.7 AS "IAP Revenue",
        SUM(c4) AS "Ad UV", SUM(c5) AS "Ad Revenue", 
        SUM(c0) as total_amount, 1 as group_num_0, 1 as group_num
    FROM (
        -- 1. 消耗端 (AppsFlyer)：利用 AppID 精准拆分
        SELECT 
            ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
            CASE 
                WHEN "te_ads_object"."app_id" = '6748138347' THEN 'iOS' 
                WHEN "te_ads_object"."app_id" = 'com.solitairemanor.secrets' THEN 'Android' 
                ELSE 'Unknown' 
            END as "OS",
            SUM(CAST(cost AS DOUBLE)) as c0,
            0 as c1, 0 as c2, 0 as c3, 0 as c4, 0 as c5, 0 as c6, 0 as c7, 0 as c8, 0 as c9, 
            0 as c10, 0 as c11, 0 as c12, 0 as c13, 0 as c14, 0 as c15, 0 as c16, 0 as c17, 
            0 as c18, 0 as c19, 0 as c20, 0 as c21, 0 as c22, 0 as c23
        FROM v_event_{project_id}
        WHERE "$part_event" = 'appsflyer_master_data' AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY 1, 2

        UNION ALL

        -- 2. 行为端 (Game Logs)：利用日志 #os 拆分
        SELECT 
            ta_date_trunc('day', ta_u.inst_t, 1) AS "$__Date_Time",
            ta_u.os_val as "OS",
            0 as c0,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'first_finish_plot', ta_ev."#user_id"))) AS DOUBLE) c1,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '10', ta_ev."#user_id"))) AS DOUBLE) c2,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '20', ta_ev."#user_id"))) AS DOUBLE) c3,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev."#user_id"))) AS DOUBLE) c4,
            CAST(SUM(CAST(IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev.revenue) AS DOUBLE)) AS DOUBLE) c5,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev."#user_id"))) AS DOUBLE) c6,
            CAST(SUM(CAST(IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev.iap_product_currency) AS DOUBLE)) AS DOUBLE) c7,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '30', ta_ev."#user_id"))) AS DOUBLE) c8,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '40', ta_ev."#user_id"))) AS DOUBLE) c9,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '50', ta_ev."#user_id"))) AS DOUBLE) c10,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '60', ta_ev."#user_id"))) AS DOUBLE) c11,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '70', ta_ev."#user_id"))) AS DOUBLE) c12,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '80', ta_ev."#user_id"))) AS DOUBLE) c13,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '90', ta_ev."#user_id"))) AS DOUBLE) c14,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '100', ta_ev."#user_id"))) AS DOUBLE) c15,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm IS NULL, ta_ev."#user_id"))) AS DOUBLE) c16,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 0 AND ta_u.ecpm < 100, ta_ev."#user_id"))) AS DOUBLE) c17,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 100 AND ta_u.ecpm < 200, ta_ev."#user_id"))) AS DOUBLE) c18,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 200 AND ta_u.ecpm < 300, ta_ev."#user_id"))) AS DOUBLE) c19,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 300 AND ta_u.ecpm < 400, ta_ev."#user_id"))) AS DOUBLE) c20,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 400 AND ta_u.ecpm < 500, ta_ev."#user_id"))) AS DOUBLE) c21,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 500, ta_ev."#user_id"))) AS DOUBLE) c22,
            CAST(COUNT(IF(ta_ev."$part_event" = 'iap_recharge_succeed', 1)) AS DOUBLE) c23
        FROM (
            SELECT "#user_id", "$part_event", "level_id", "ad_format", "revenue", "iap_product_currency", "#app_version"
            FROM v_event_{project_id} 
            WHERE "$part_event" IN ('first_finish_plot', 'level_start', 'applovin_ad_revenue_impression_level', 'iap_recharge_succeed')
              AND "$part_date" BETWEEN '{start_date}' AND '{today_str}' 
        ) ta_ev 
        INNER JOIN (
            SELECT ev."#user_id", 
                   CASE 
                       WHEN LOWER(ev."#os") LIKE '%%ios%%' THEN 'iOS' 
                       ELSE 'Android' 
                   END as os_val,
                   min(ev."#event_time") AS inst_t, 
                   arbitrary(u.first_rv_ecpm) as ecpm,
                   u."app_version_first" AS v_first
            FROM v_event_{project_id} ev
            LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
            WHERE ev."$part_event" = 'first_finish_plot' AND ev."$part_date" BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 1, 2, 5
        ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
        WHERE ta_ev."#app_version" = ta_u.v_first
        GROUP BY 1, 2
    )
    GROUP BY 1, 2, 3, 4
)
ORDER BY "Date" DESC, "OS" ASC
"""

    @staticmethod
    def get_advertising_report_sql(project_id, start_date, end_date, dimension="campaign_name"):
        """
        广告层级 SQL (保持原逻辑，因为广告层级自带 te_ads_object，通常已有 OS 属性)
        """
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        field_mapping = {"广告计划": "campaign_name", "广告组": "ad_group_name", "广告创意": "ad_name"}
        real_field = field_mapping.get(dimension, dimension)
        dim_raw = f'"te_ads_object"."{real_field}"'
        dim_with_u = f'u."te_ads_object"."{real_field}"'
        
        return f"""
/* sessionProperties: {{"ignore_downstream_preferences":"true"}} */
SELECT * FROM (
    SELECT *, count("Cost") OVER () group_num_0, count(1) OVER () group_num 
    FROM (
        SELECT 
            format_datetime("$__Date_Time", 'yyyy-MM-dd') AS "Date", group_0 AS "Dimension Value", media_source AS "Media Source",
            array_join(array_distinct(all_os), ', ') AS "OS",
            internal_amount_0 AS "Cost", internal_amount_1 AS "Plot UV", 
            internal_amount_16 AS "ECPM_Null", internal_amount_17 AS "ECPM_0_100", internal_amount_18 AS "ECPM_100_200",
            internal_amount_19 AS "ECPM_200_300", internal_amount_20 AS "ECPM_300_400", internal_amount_21 AS "ECPM_400_500",
            internal_amount_22 AS "ECPM_500+",
            internal_amount_2 AS "L10 UV", internal_amount_3 AS "L20 UV", internal_amount_8 AS "L30 UV", 
            internal_amount_9 AS "L40 UV", internal_amount_10 AS "L50 UV", internal_amount_11 AS "L60 UV",
            internal_amount_12 AS "L70 UV", internal_amount_13 AS "L80 UV", internal_amount_14 AS "L90 UV",
            internal_amount_15 AS "L100 UV",
            internal_amount_6 AS "IAP UV", internal_amount_23 AS "IAP Times", 
            CAST(coalesce(internal_amount_7, 0) AS DOUBLE)/100*0.7 AS "IAP Revenue",
            internal_amount_4 AS "Ad UV", internal_amount_5 AS "Ad Revenue", 
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
                SELECT 
                    CASE WHEN "te_ads_object" IS NULL OR {dim_raw} IS NULL THEN '自然量' ELSE {dim_raw} END AS group_0,
                    CASE WHEN "te_ads_object" IS NULL OR "te_ads_object"."media_source" IS NULL THEN 'Organic' ELSE "te_ads_object"."media_source" END AS media_source,
                    ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
                    CAST(coalesce(SUM(CAST(cost AS DOUBLE)), 0) AS DOUBLE) internal_amount_0,
                    NULL internal_amount_1, NULL internal_amount_2, NULL internal_amount_3, NULL internal_amount_4, 
                    NULL internal_amount_5, NULL internal_amount_6, NULL internal_amount_7, NULL internal_amount_8, 
                    NULL internal_amount_9, NULL internal_amount_10, NULL internal_amount_11, NULL internal_amount_12, 
                    NULL internal_amount_13, NULL internal_amount_14, NULL internal_amount_15, NULL internal_amount_16, 
                    NULL internal_amount_17, NULL internal_amount_18, NULL internal_amount_19, NULL internal_amount_20, 
                    NULL internal_amount_21, NULL internal_amount_22, NULL internal_amount_23, NULL as os_val
                FROM v_event_{project_id} 
                WHERE "$part_event" = 'appsflyer_master_data' AND "$part_date" BETWEEN '{start_date}' AND '{end_date}'
                GROUP BY 1, 2, 3
                UNION ALL
                SELECT 
                    ta_u.group_0, ta_u.media_source, ta_date_trunc('day', ta_u.inst_t, 1) AS "$__Date_Time",
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
                    FROM v_event_{project_id} 
                    WHERE "$part_event" IN ('first_finish_plot', 'level_start', 'applovin_ad_revenue_impression_level', 'iap_recharge_succeed')
                      AND "$part_date" BETWEEN '{start_date}' AND '{today_str}' 
                ) ta_ev 
                INNER JOIN (
                    SELECT ev."#user_id", 
                        CASE WHEN u."te_ads_object" IS NULL OR {dim_with_u} IS NULL THEN '自然量' ELSE {dim_with_u} END AS group_0, 
                        CASE WHEN u."te_ads_object" IS NULL OR u."te_ads_object"."media_source" IS NULL THEN 'Organic' ELSE u."te_ads_object"."media_source" END AS media_source,
                        u."app_version_first" AS v_first, min(ev."#event_time") AS inst_t, arbitrary(ev."#os") as os_val, arbitrary(u.first_rv_ecpm) as ecpm
                    FROM v_event_{project_id} ev
                    LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
                    WHERE ev."$part_event" = 'first_finish_plot' AND ev."$part_date" BETWEEN '{start_date}' AND '{end_date}'
                    GROUP BY 1, 2, 3, 4
                ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
                WHERE ta_ev."#app_version" = ta_u.v_first
                GROUP BY 1, 2, 3
            ) 
            WHERE "$__Date_Time" >= TIMESTAMP '{start_date}' AND "$__Date_Time" < date_add('day', 1, TIMESTAMP '{end_date}')
            GROUP BY group_0, media_source, "$__Date_Time"
        )
        WHERE (internal_amount_0 > 0 OR internal_amount_1 > 0)
    )
) ORDER BY "Date" DESC, total_amount DESC LIMIT 1000
"""
