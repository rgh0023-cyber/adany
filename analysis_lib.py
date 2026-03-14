import pandas as pd
import datetime

class AdAnalysis:
    @staticmethod
    def get_absolute_summary_sql(project_id, start_date, end_date):
        """
        全量汇总 SQL (Cohort 模式)：
        - 消耗端：利用 app_id (6748138347 为 iOS) 判定平台。
        - 行为端：利用日志自带的 #os 判定平台。
        """
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        return f"""
/* sessionProperties: {{ "ignore_downstream_preferences":"true" }} */
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
        -- 1. 锁定时间范围内的广告消耗 (通过 AppID 拆分 OS)
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

        -- 2. 统计这批新增用户从激活到今日(Today)的所有累积行为 (通过日志原生属性拆分 OS)
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
                   u."app_version_first" AS v_first, 
                   min(ev."#event_time") AS inst_t, 
                   arbitrary(u.first_rv_ecpm) as ecpm
            FROM v_event_{project_id} ev
            LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
            WHERE ev."$part_event" = 'first_finish_plot' AND ev."$part_date" BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 1, 2, 3
        ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
        WHERE ta_ev."#app_version" = ta_u.v_first
        GROUP BY 1, 2
    )
    WHERE "$__Date_Time" >= TIMESTAMP '{start_date}' AND "$__Date_Time" < date_add('day', 1, TIMESTAMP '{end_date}')
    GROUP BY 1, 4
)
ORDER BY "Date" DESC, "OS" ASC
"""

    @staticmethod
    def get_advertising_report_sql(project_id, start_date, end_date, dimension="campaign_name"):
        # 广告报表部分逻辑已经很成熟，不需要改动，保持你发给我的原样即可
        pass
