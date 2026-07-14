import datetime


class AdAnalysis:
    """
    Cohort SQL：
    - get_absolute_summary_sql（全量）：消耗按 appsflyer **app_id** 拆 OS，与 cohort 行为（#os）分轨 UNION 后按 Date+OS 汇总，
      避免「仅有消耗、无用户」的消耗与用户层级硬拼导致 OS 空/错位。
    - get_cohort_fine_grain_sql / get_advertising_report_sql：广告穿透，消耗与行为均按 计划×组×创意×media×日 与用户 cohort 对齐。
    - Cohort 口径：用户行为（Plot UV、关卡、IAP 等）仅来自用户相关事件；**仅 Cost** 由 `appsflyer_master_data.cost`
      与（自 FB_COST_PART_DATE_CUTOFF 起）`facebook_ad_level_data_by_platform.amount_spent_usd`、
      （自 UNITY_COST_PART_DATE_CUTOFF 起）`unity_ads_api_data.spend` 分段合并。
    - 全量汇总：同一 Date×OS 下对各段消耗 **SUM(c0)**，与 cohort 行为段 **SUM** 合并为一张表。
    - 广告穿透：Facebook 消耗 OS 用 **account_name** → **app_id** → **#os**；
      Unity 消耗 OS 仅用事件顶层 **platform** / **store**（先 lower 再匹配，兼容 iOS/IOS/ios），再 app_id、#os 兜底；
      归因计划/组/创意仍只读 **te_ads_object**。
    - 广告穿透媒体：Facebook 系统一为 **`facebook`**；Unity 系统一为 **`unityads_int`**，避免与 cohort 键不一致。
    """

    # 事件日 >= 此日：Facebook 消耗并入 facebook_ad_level_data_by_platform
    FB_COST_PART_DATE_CUTOFF = "2026-06-03"
    # 事件日 >= 此日：Unity 消耗并入 unity_ads_api_data（AF 侧 unityads_int 无 cost）
    UNITY_COST_PART_DATE_CUTOFF = "2026-01-01"

    @staticmethod
    def _unity_os_cost_sql(te_obj='"te_ads_object"'):
        """Unity API 消耗 OS：仅事件顶层 platform / store（不在 te_ads_object 内）；先 lower 再匹配。"""
        plat = (
            "lower(trim(coalesce("
            "cast(\"platform\" AS VARCHAR), "
            "cast(platform AS VARCHAR), "
            "''"
            ")))"
        )
        store = (
            "lower(trim(coalesce("
            "cast(\"store\" AS VARCHAR), "
            "cast(store AS VARCHAR), "
            "''"
            ")))"
        )
        os_raw = "lower(trim(coalesce(cast(\"#os\" AS VARCHAR), '')))"
        return (
            f"CASE "
            f"WHEN {plat} IN ('ios', 'iphone', 'ipad', 'ipados', 'apple', 'itunes') THEN 'iOS' "
            f"WHEN {plat} LIKE 'ios%' OR {plat} LIKE 'iphone%' OR {plat} LIKE 'ipad%' THEN 'iOS' "
            f"WHEN {store} IN ('apple', 'ios', 'itunes', 'app_store', 'appstore') THEN 'iOS' "
            f"WHEN {store} LIKE 'apple%' OR {store} LIKE 'ios%' THEN 'iOS' "
            f"WHEN {plat} IN ('android', 'andr') OR {plat} LIKE 'android%' THEN 'Android' "
            f"WHEN {store} IN ('google', 'android', 'google_play', 'play') THEN 'Android' "
            f"WHEN {store} LIKE 'google%' OR {store} LIKE 'android%' THEN 'Android' "
            f"WHEN {te_obj}.app_id = 'id6748138347' THEN 'iOS' "
            f"WHEN {te_obj}.app_id = 'com.solitairemanor.secrets' THEN 'Android' "
            f"WHEN {os_raw} IN ('ios', 'apple', 'iphone', 'ipad', 'ipados') THEN 'iOS' "
            f"WHEN {os_raw} IN ('android') OR {os_raw} LIKE 'android%' THEN 'Android' "
            "ELSE 'Unknown' END"
        )

    @staticmethod
    def get_cohort_fine_grain_sql(project_id, start_date, end_date):
        """
        广告穿透专用：cohort 用户按 first_start_up 锁定，归因字段来自 v_user.te_ads_object（计划/组/创意）；
        缺归因记「自然量」。消耗与行为在同一五维键上 UNION。
        侧边栏「广告计划/组/创意」均调用本 SQL，不改变语句；展示粒度由 app 层 aggregate_cohort_by_dim_choice 处理。
        结果列顺序需与 data_processor.expected_cols 一致。
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        E = '"te_ads_object"'
        U = 'u."te_ads_object"'
        # 归因桶约定：
        # 1) 仅当 campaign/ad_group/ad_name 为 NULL 才算「自然量」
        # 2) 若字段存在但为空字符串或 '-'，同样归为「自然量」
        camp_e = (
            f"CASE WHEN {E} IS NULL OR {E}.\"campaign_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({E}.\"campaign_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {E}.\"campaign_name\" END"
        )
        grp_e = (
            f"CASE WHEN {E} IS NULL OR {E}.\"ad_group_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({E}.\"ad_group_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {E}.\"ad_group_name\" END"
        )
        cre_e = (
            f"CASE WHEN {E} IS NULL OR {E}.\"ad_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({E}.\"ad_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {E}.\"ad_name\" END"
        )
        camp_u = (
            f"CASE WHEN {U} IS NULL OR {U}.\"campaign_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({U}.\"campaign_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {U}.\"campaign_name\" END"
        )
        grp_u = (
            f"CASE WHEN {U} IS NULL OR {U}.\"ad_group_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({U}.\"ad_group_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {U}.\"ad_group_name\" END"
        )
        cre_u = (
            f"CASE WHEN {U} IS NULL OR {U}.\"ad_name\" IS NULL THEN '自然量' "
            f"WHEN lower(trim(coalesce(cast({U}.\"ad_name\" AS VARCHAR), ''))) IN ('-', '') THEN '自然量' "
            f"ELSE {U}.\"ad_name\" END"
        )
        # 自然量判定仍看原始 media 是否空；Facebook/Unity 系媒体统一，避免同计划多字符串拆行
        _ms_lower_e = f"lower(trim(coalesce(cast({E}.\"media_source\" AS VARCHAR), '')))"
        _is_fb_media_e = (
            f"({_ms_lower_e} LIKE '%facebook%' OR {_ms_lower_e} LIKE '%instagram%' "
            f"OR {_ms_lower_e} LIKE '%audience network%' OR {_ms_lower_e} IN ('restricted', 'fb') "
            f"OR {_ms_lower_e} LIKE 'meta%')"
        )
        _is_unity_media_e = (
            f"({_ms_lower_e} LIKE '%unity%' OR {_ms_lower_e} IN ('unityads_int', 'unityads'))"
        )
        _ms_lower_u = f"lower(trim(coalesce(cast({U}.\"media_source\" AS VARCHAR), '')))"
        _is_fb_media_u = (
            f"({_ms_lower_u} LIKE '%facebook%' OR {_ms_lower_u} LIKE '%instagram%' "
            f"OR {_ms_lower_u} LIKE '%audience network%' OR {_ms_lower_u} IN ('restricted', 'fb') "
            f"OR {_ms_lower_u} LIKE 'meta%')"
        )
        _is_unity_media_u = (
            f"({_ms_lower_u} LIKE '%unity%' OR {_ms_lower_u} IN ('unityads_int', 'unityads'))"
        )
        media_e = (
            f"CASE WHEN {E} IS NULL "
            f"OR lower(trim(coalesce(cast({E}.\"campaign_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({E}.\"ad_group_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({E}.\"ad_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({E}.\"media_source\" AS VARCHAR), ''))) IN ('-', '') "
            f"THEN 'organic' WHEN {_is_fb_media_e} THEN 'facebook' "
            f"WHEN {_is_unity_media_e} THEN 'unityads_int' ELSE {E}.\"media_source\" END"
        )
        media_u = (
            f"CASE WHEN {U} IS NULL "
            f"OR lower(trim(coalesce(cast({U}.\"campaign_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({U}.\"ad_group_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({U}.\"ad_name\" AS VARCHAR), ''))) IN ('-', '') "
            f"OR lower(trim(coalesce(cast({U}.\"media_source\" AS VARCHAR), ''))) IN ('-', '') "
            f"THEN 'organic' WHEN {_is_fb_media_u} THEN 'facebook' "
            f"WHEN {_is_unity_media_u} THEN 'unityads_int' ELSE {U}.\"media_source\" END"
        )
        os_u = (
            "CASE WHEN lower(COALESCE(CAST(arbitrary(ev.\"#os\") AS VARCHAR), '')) IN ('ios', 'apple') THEN 'iOS' "
            "WHEN lower(COALESCE(CAST(arbitrary(ev.\"#os\") AS VARCHAR), '')) IN ('android') THEN 'Android' "
            "ELSE 'Unknown' END"
        )
        # 费用事件上用于判端的「账户/名称」小写串（数数属性多为双引号 account_name）
        # 须用 cast(\"account_name\" …)，勿写成 \\\"…\\\"，否则 SQL 里会出现字面量 \，Open SQL 解析报错
        _acct_nm_lower = (
            "lower(trim(coalesce(cast(\"account_name\" AS VARCHAR), '')))"
        )
        # account_name 判端：如 Bluefocus - Game - iOS - …（小写后含 -ios-、 ios 等分隔形式）；不用 regexp_like，避免数数 SQL 对反斜杠解析报错
        _acct_is_ios = (
            f"({_acct_nm_lower} LIKE '% ios %' OR {_acct_nm_lower} LIKE '%-ios-%' OR {_acct_nm_lower} LIKE '%-ios %' "
            f"OR {_acct_nm_lower} LIKE '% ios-%' OR {_acct_nm_lower} LIKE 'ios %' OR {_acct_nm_lower} LIKE 'ios-%' "
            f"OR {_acct_nm_lower} LIKE '%-ios' OR {_acct_nm_lower} = 'ios' "
            f"OR strpos({_acct_nm_lower}, 'iphone') > 0 OR strpos({_acct_nm_lower}, 'ipad') > 0 "
            f"OR strpos({_acct_nm_lower}, 'ipados') > 0 OR strpos({_acct_nm_lower}, 'apple') > 0 "
            f"OR strpos({_acct_nm_lower}, '苹果') > 0)"
        )
        _acct_is_android = (
            f"({_acct_nm_lower} LIKE '% android %' OR {_acct_nm_lower} LIKE '%-android-%' OR {_acct_nm_lower} LIKE '%-android %' "
            f"OR {_acct_nm_lower} LIKE '% android-%' OR {_acct_nm_lower} LIKE 'android %' OR {_acct_nm_lower} LIKE 'android-%' "
            f"OR {_acct_nm_lower} LIKE '%-android' OR {_acct_nm_lower} = 'android' "
            f"OR strpos({_acct_nm_lower}, '安卓') > 0)"
        )
        # 消耗侧 OS（AppsFlyer）：account_name 判端（AF 行常无 #os）→ #os → app_id
        os_cost = (
            f"CASE WHEN {_acct_is_ios} THEN 'iOS' "
            f"WHEN {_acct_is_android} THEN 'Android' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('ios', 'apple') THEN 'iOS' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('android') THEN 'Android' "
            f"WHEN {E}.app_id = 'id6748138347' THEN 'iOS' "
            f"WHEN {E}.app_id = 'com.solitairemanor.secrets' THEN 'Android' "
            "ELSE 'Unknown' END"
        )
        # Facebook API 费用：account_name 规则优先，再 app_id、#os
        os_cost_api = (
            f"CASE WHEN {_acct_is_ios} THEN 'iOS' "
            f"WHEN {_acct_is_android} THEN 'Android' "
            f"WHEN {E}.app_id = 'id6748138347' THEN 'iOS' "
            f"WHEN {E}.app_id = 'com.solitairemanor.secrets' THEN 'Android' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('ios', 'apple') THEN 'iOS' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('android') THEN 'Android' "
            "ELSE 'Unknown' END"
        )
        os_cost_unity = AdAnalysis._unity_os_cost_sql(E)
        fb_cut = AdAnalysis.FB_COST_PART_DATE_CUTOFF
        unity_cut = AdAnalysis.UNITY_COST_PART_DATE_CUTOFF

        return f"""
/* sessionProperties: {{"ignore_downstream_preferences":"true"}} */
SELECT * FROM (
    SELECT *, count("Cost") OVER () group_num_0, count(1) OVER () group_num
    FROM (
        SELECT
            format_datetime("$__Date_Time", 'yyyy-MM-dd') AS "Date",
            dim_ad_name AS "Dimension Value",
            media_source AS "Media Source",
            os_val AS "OS",
            CAST(NULL AS VARCHAR) AS "维度名称_全部",
            dim_campaign AS "维度名称_广告计划",
            dim_ad_group AS "维度名称_广告组",
            dim_ad_name AS "维度名称_广告创意",
            internal_amount_0 AS "Cost", internal_amount_1 AS "Plot UV",
            internal_amount_16 AS "ECPM_Null", internal_amount_17 AS "ECPM_0_100", internal_amount_18 AS "ECPM_100_200",
            internal_amount_19 AS "ECPM_200_300", internal_amount_20 AS "ECPM_300_400", internal_amount_21 AS "ECPM_400_500",
            internal_amount_22 AS "ECPM_500+",
            internal_amount_2 AS "L10 UV", internal_amount_3 AS "L20 UV", internal_amount_8 AS "L30 UV",
            internal_amount_9 AS "L40 UV", internal_amount_10 AS "L50 UV", internal_amount_11 AS "L60 UV",
            internal_amount_12 AS "L70 UV", internal_amount_13 AS "L80 UV", internal_amount_14 AS "L90 UV",
            internal_amount_15 AS "L100 UV",
            internal_amount_6 AS "IAP UV", internal_amount_24 AS "IAP_UV_D0", internal_amount_23 AS "IAP Times",
            CAST(coalesce(internal_amount_7, 0) AS DOUBLE)/100*0.7 AS "IAP Revenue",
            internal_amount_4 AS "Ad UV", internal_amount_5 AS "Ad Revenue",
            sum(IF(is_finite(internal_amount_0), internal_amount_0, 0)) OVER (
                PARTITION BY "$__Date_Time", dim_campaign, dim_ad_group, dim_ad_name, media_source, os_val
            ) as total_amount
        FROM (
            SELECT dim_campaign, dim_ad_group, dim_ad_name, media_source, os_val, "$__Date_Time",
                SUM(coalesce(internal_amount_0, 0)) internal_amount_0, SUM(coalesce(internal_amount_1, 0)) internal_amount_1,
                SUM(coalesce(internal_amount_2, 0)) internal_amount_2, SUM(coalesce(internal_amount_3, 0)) internal_amount_3,
                SUM(coalesce(internal_amount_4, 0)) internal_amount_4, SUM(coalesce(internal_amount_5, 0)) internal_amount_5,
                SUM(coalesce(internal_amount_6, 0)) internal_amount_6, SUM(coalesce(internal_amount_7, 0)) internal_amount_7,
                SUM(coalesce(internal_amount_8, 0)) internal_amount_8, SUM(coalesce(internal_amount_9, 0)) internal_amount_9,
                SUM(coalesce(internal_amount_10, 0)) internal_amount_10, SUM(coalesce(internal_amount_11, 0)) internal_amount_11,
                SUM(coalesce(internal_amount_12, 0)) internal_amount_12, SUM(coalesce(internal_amount_13, 0)) internal_amount_13,
                SUM(coalesce(internal_amount_14, 0)) internal_amount_14, SUM(coalesce(internal_amount_15, 0)) internal_amount_15,
                SUM(coalesce(internal_amount_16, 0)) internal_amount_16, SUM(coalesce(internal_amount_17, 0)) internal_amount_17,
                SUM(coalesce(internal_amount_18, 0)) internal_amount_18, SUM(coalesce(internal_amount_19, 0)) internal_amount_19,
                SUM(coalesce(internal_amount_20, 0)) internal_amount_20, SUM(coalesce(internal_amount_21, 0)) internal_amount_21,
                SUM(coalesce(internal_amount_22, 0)) internal_amount_22, SUM(coalesce(internal_amount_23, 0)) internal_amount_23,
                SUM(coalesce(internal_amount_24, 0)) internal_amount_24
            FROM (
                -- 消耗(Event Time)：appsflyer_master_data（6/3 后已无 Facebook 成本，无需再互斥剔除）
                SELECT
                    {camp_e} AS dim_campaign,
                    {grp_e} AS dim_ad_group,
                    {cre_e} AS dim_ad_name,
                    {media_e} AS media_source,
                    ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
                    CAST(coalesce(SUM(CAST(cost AS DOUBLE)), 0) AS DOUBLE) internal_amount_0,
                    NULL internal_amount_1, NULL internal_amount_2, NULL internal_amount_3, NULL internal_amount_4,
                    NULL internal_amount_5, NULL internal_amount_6, NULL internal_amount_7, NULL internal_amount_8,
                    NULL internal_amount_9, NULL internal_amount_10, NULL internal_amount_11, NULL internal_amount_12,
                    NULL internal_amount_13, NULL internal_amount_14, NULL internal_amount_15, NULL internal_amount_16,
                    NULL internal_amount_17, NULL internal_amount_18, NULL internal_amount_19, NULL internal_amount_20,
                    NULL internal_amount_21, NULL internal_amount_22, NULL internal_amount_23,
                    NULL internal_amount_24, {os_cost} as os_val
                FROM v_event_{project_id}
                WHERE "$part_event" = 'appsflyer_master_data'
                  AND "$part_date" >= '2026-01-01'
                  AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
                  AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
                GROUP BY 1, 2, 3, 4, 5, 31
                UNION ALL
                -- 自 {fb_cut} 起 Facebook 消耗：媒体固定为 facebook（不读 te_ads_object.media_source，避免与 cohort 键不一致）
                SELECT
                    {camp_e} AS dim_campaign,
                    {grp_e} AS dim_ad_group,
                    {cre_e} AS dim_ad_name,
                    'facebook' AS media_source,
                    ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
                    CAST(coalesce(SUM(CAST(coalesce("amount_spent_usd", amount_spent_usd) AS DOUBLE)), 0) AS DOUBLE) internal_amount_0,
                    NULL internal_amount_1, NULL internal_amount_2, NULL internal_amount_3, NULL internal_amount_4,
                    NULL internal_amount_5, NULL internal_amount_6, NULL internal_amount_7, NULL internal_amount_8,
                    NULL internal_amount_9, NULL internal_amount_10, NULL internal_amount_11, NULL internal_amount_12,
                    NULL internal_amount_13, NULL internal_amount_14, NULL internal_amount_15, NULL internal_amount_16,
                    NULL internal_amount_17, NULL internal_amount_18, NULL internal_amount_19, NULL internal_amount_20,
                    NULL internal_amount_21, NULL internal_amount_22, NULL internal_amount_23,
                    NULL internal_amount_24, {os_cost_api} as os_val
                FROM v_event_{project_id}
                WHERE "$part_event" = 'facebook_ad_level_data_by_platform'
                  AND "$part_date" >= '2026-01-01'
                  AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{fb_cut}'
                  AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
                  AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
                GROUP BY 1, 2, 3, 4, 5, 31
                UNION ALL
                -- 自 {unity_cut} 起 Unity 消耗：媒体 unityads_int；归因 te_ads_object；OS 读 platform
                SELECT
                    {camp_e} AS dim_campaign,
                    {grp_e} AS dim_ad_group,
                    {cre_e} AS dim_ad_name,
                    'unityads_int' AS media_source,
                    ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
                    CAST(coalesce(SUM(CAST(coalesce("spend", spend) AS DOUBLE)), 0) AS DOUBLE) internal_amount_0,
                    NULL internal_amount_1, NULL internal_amount_2, NULL internal_amount_3, NULL internal_amount_4,
                    NULL internal_amount_5, NULL internal_amount_6, NULL internal_amount_7, NULL internal_amount_8,
                    NULL internal_amount_9, NULL internal_amount_10, NULL internal_amount_11, NULL internal_amount_12,
                    NULL internal_amount_13, NULL internal_amount_14, NULL internal_amount_15, NULL internal_amount_16,
                    NULL internal_amount_17, NULL internal_amount_18, NULL internal_amount_19, NULL internal_amount_20,
                    NULL internal_amount_21, NULL internal_amount_22, NULL internal_amount_23,
                    NULL internal_amount_24, {os_cost_unity} as os_val
                FROM v_event_{project_id}
                WHERE "$part_event" = 'unity_ads_api_data'
                  AND "$part_date" >= '2026-01-01'
                  AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{unity_cut}'
                  AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
                  AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
                GROUP BY 1, 2, 3, 4, 5, 31
                UNION ALL
                -- 行为(Cohort Time, 统计至今日)
                SELECT
                    ta_u.dim_campaign, ta_u.dim_ad_group, ta_u.dim_ad_name, ta_u.media_source,
                    ta_date_trunc('day', ta_u.inst_t, 1) AS "$__Date_Time",
                    NULL internal_amount_0,
                    CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'first_start_up', ta_ev."#user_id"))) AS DOUBLE) internal_amount_1,
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
                    CAST(COUNT(DISTINCT (IF(ta_u.first_iap_t IS NOT NULL AND ta_date_trunc('day', ta_u.first_iap_t, 1) = ta_date_trunc('day', ta_u.inst_t, 1), ta_ev."#user_id"))) AS DOUBLE) internal_amount_24,
                    ta_u.os_val as os_val
                FROM (
                    SELECT "#user_id", "$part_event", "level_id", "ad_format", "revenue", "iap_product_currency", "#app_version"
                    FROM v_event_{project_id}
                    WHERE "$part_event" IN ('first_start_up', 'level_start', 'applovin_ad_revenue_impression_level', 'iap_recharge_succeed')
                      AND "$part_date" >= '2026-01-01'
                      AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce("#zone_offset", 0) AS INTEGER), "#event_time"), 1) >= TIMESTAMP '{start_date}'
                      AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce("#zone_offset", 0) AS INTEGER), "#event_time"), 1) < date_add('day', 1, TIMESTAMP '{today_str}')
                ) ta_ev
                INNER JOIN (
                    SELECT cohort."#user_id", cohort.dim_campaign, cohort.dim_ad_group, cohort.dim_ad_name,
                           cohort.media_source, cohort.v_first, cohort.inst_t, cohort.os_val, cohort.ecpm, fi.first_iap_t
                    FROM (
                        SELECT ev."#user_id",
                            {camp_u} AS dim_campaign,
                            {grp_u} AS dim_ad_group,
                            {cre_u} AS dim_ad_name,
                            {media_u} AS media_source,
                            u."app_version_first" AS v_first,
                            min(date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time")) AS inst_t,
                            {os_u} as os_val,
                            arbitrary(u.first_rv_ecpm) as ecpm
                        FROM v_event_{project_id} ev
                        LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
                        WHERE ev."$part_event" = 'first_start_up'
                          AND ev."$part_date" >= '2026-01-01'
                          AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) >= TIMESTAMP '{start_date}'
                          AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) < date_add('day', 1, TIMESTAMP '{end_date}')
                          AND u."is_test" = false
                          AND coalesce(CAST(u."#account_id" AS VARCHAR), '') NOT IN (
                              '86122677072314368', '85632127382601728', '85631822439923712'
                          )
                        GROUP BY 1, 2, 3, 4, 5, 6
                    ) cohort
                    LEFT JOIN (
                        SELECT i."#user_id", u2."app_version_first" AS v_first,
                               min(date_add('hour', -8 - CAST(coalesce(i."#zone_offset", 0) AS INTEGER), i."#event_time")) AS first_iap_t
                        FROM v_event_{project_id} i
                        LEFT JOIN v_user_{project_id} u2 ON i."#user_id" = u2."#user_id"
                        WHERE i."$part_event" = 'iap_recharge_succeed'
                          AND i."$part_date" >= '2026-01-01'
                          AND i."#app_version" = u2."app_version_first"
                        GROUP BY 1, 2
                    ) fi ON cohort."#user_id" = fi."#user_id" AND cohort.v_first = fi.v_first
                ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
                WHERE ta_ev."#app_version" = ta_u.v_first
                GROUP BY
                    ta_u.dim_campaign,
                    ta_u.dim_ad_group,
                    ta_u.dim_ad_name,
                    ta_u.media_source,
                    ta_date_trunc('day', ta_u.inst_t, 1),
                    ta_u.os_val
            )
            WHERE "$__Date_Time" >= TIMESTAMP '{start_date}' AND "$__Date_Time" < date_add('day', 1, TIMESTAMP '{end_date}')
            GROUP BY dim_campaign, dim_ad_group, dim_ad_name, media_source, os_val, "$__Date_Time"
        )
        WHERE (internal_amount_0 > 0 OR internal_amount_1 > 0)
    )
) ORDER BY "Date" DESC, total_amount DESC LIMIT 10000
"""

    @staticmethod
    def get_absolute_summary_sql(project_id, start_date, end_date):
        """
        全量汇总：消耗与用户行为分轨聚合后再按 Date+OS 合并（口径与早期版本一致）。
        结果列顺序与 data_processor.expected_cols 一致（含四维占位列，库内为 NULL）。
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        fb_cut = AdAnalysis.FB_COST_PART_DATE_CUTOFF
        unity_cut = AdAnalysis.UNITY_COST_PART_DATE_CUTOFF
        _abs_acct_ln = "lower(trim(coalesce(cast(\"account_name\" AS VARCHAR), '')))"
        _abs_acct_ios = (
            f"({_abs_acct_ln} LIKE '% ios %' OR {_abs_acct_ln} LIKE '%-ios-%' OR {_abs_acct_ln} LIKE '%-ios %' "
            f"OR {_abs_acct_ln} LIKE '% ios-%' OR {_abs_acct_ln} LIKE 'ios %' OR {_abs_acct_ln} LIKE 'ios-%' "
            f"OR {_abs_acct_ln} LIKE '%-ios' OR {_abs_acct_ln} = 'ios' "
            f"OR strpos({_abs_acct_ln}, 'iphone') > 0 OR strpos({_abs_acct_ln}, 'ipad') > 0 "
            f"OR strpos({_abs_acct_ln}, 'ipados') > 0 OR strpos({_abs_acct_ln}, 'apple') > 0 "
            f"OR strpos({_abs_acct_ln}, '苹果') > 0)"
        )
        _abs_acct_android = (
            f"({_abs_acct_ln} LIKE '% android %' OR {_abs_acct_ln} LIKE '%-android-%' OR {_abs_acct_ln} LIKE '%-android %' "
            f"OR {_abs_acct_ln} LIKE '% android-%' OR {_abs_acct_ln} LIKE 'android %' OR {_abs_acct_ln} LIKE 'android-%' "
            f"OR {_abs_acct_ln} LIKE '%-android' OR {_abs_acct_ln} = 'android' "
            f"OR strpos({_abs_acct_ln}, '安卓') > 0)"
        )
        # 全量 AppsFlyer 消耗：account_name → #os → app_id（与穿透 os_cost 一致）
        os_cost_abs = (
            f"CASE WHEN {_abs_acct_ios} THEN 'iOS' "
            f"WHEN {_abs_acct_android} THEN 'Android' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('ios', 'apple') THEN 'iOS' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('android') THEN 'Android' "
            "WHEN te_ads_object.app_id = 'id6748138347' THEN 'iOS' "
            "WHEN te_ads_object.app_id = 'com.solitairemanor.secrets' THEN 'Android' "
            "ELSE 'Unknown' END"
        )
        # 全量 Facebook API 消耗：account_name 扩展匹配，再 app_id、#os
        os_cost_abs_api = (
            f"CASE WHEN {_abs_acct_ios} THEN 'iOS' "
            f"WHEN {_abs_acct_android} THEN 'Android' "
            "WHEN te_ads_object.app_id = 'id6748138347' THEN 'iOS' "
            "WHEN te_ads_object.app_id = 'com.solitairemanor.secrets' THEN 'Android' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('ios', 'apple') THEN 'iOS' "
            "WHEN lower(trim(coalesce(cast(\"#os\" AS VARCHAR), ''))) IN ('android') THEN 'Android' "
            "ELSE 'Unknown' END"
        )
        os_cost_abs_unity = AdAnalysis._unity_os_cost_sql("te_ads_object")
        return f"""
/* sessionProperties: {{"ignore_downstream_preferences":"true"}} */
SELECT * FROM (
    SELECT
        format_datetime("$__Date_Time", 'yyyy-MM-dd') AS "Date",
        arbitrary('Total') AS "Dimension Value",
        arbitrary(CAST(NULL AS VARCHAR)) AS "Media Source",
        "$__OS" AS "OS",
        arbitrary(CAST(NULL AS VARCHAR)) AS "维度名称_全部",
        arbitrary(CAST(NULL AS VARCHAR)) AS "维度名称_广告计划",
        arbitrary(CAST(NULL AS VARCHAR)) AS "维度名称_广告组",
        arbitrary(CAST(NULL AS VARCHAR)) AS "维度名称_广告创意",
        SUM(c0) AS "Cost", SUM(c1) AS "Plot UV",
        SUM(c16) AS "ECPM_Null", SUM(c17) AS "ECPM_0_100", SUM(c18) AS "ECPM_100_200",
        SUM(c19) AS "ECPM_200_300", SUM(c20) AS "ECPM_300_400", SUM(c21) AS "ECPM_400_500", SUM(c22) AS "ECPM_500+",
        SUM(c2) AS "L10 UV", SUM(c3) AS "L20 UV", SUM(c8) AS "L30 UV", SUM(c9) AS "L40 UV",
        SUM(c10) AS "L50 UV", SUM(c11) AS "L60 UV", SUM(c12) AS "L70 UV", SUM(c13) AS "L80 UV",
        SUM(c14) AS "L90 UV", SUM(c15) AS "L100 UV",
        SUM(c6) AS "IAP UV", SUM(c24) AS "IAP_UV_D0", SUM(c23) AS "IAP Times", SUM(c7)/100*0.7 AS "IAP Revenue",
        SUM(c4) AS "Ad UV", SUM(c5) AS "Ad Revenue",
        SUM(c0) AS total_amount, 1 AS group_num_0, 1 AS group_num
    FROM (
        SELECT
            ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
            {os_cost_abs} AS "$__OS",
            SUM(CAST(cost AS DOUBLE)) AS c0,
            0 AS c1, 0 AS c2, 0 AS c3, 0 AS c4, 0 AS c5, 0 AS c6, 0 AS c7, 0 AS c8, 0 AS c9,
            0 AS c10, 0 AS c11, 0 AS c12, 0 AS c13, 0 AS c14, 0 AS c15, 0 AS c16, 0 AS c17,
            0 AS c18, 0 AS c19, 0 AS c20, 0 AS c21, 0 AS c22, 0 AS c23, 0 AS c24
        FROM v_event_{project_id}
        WHERE "$part_event" = 'appsflyer_master_data'
          AND "$part_date" >= '2026-01-01'
          AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
          AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
        GROUP BY 1, 2
        UNION ALL
        SELECT
            ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
            {os_cost_abs_api} AS "$__OS",
            SUM(CAST(coalesce("amount_spent_usd", amount_spent_usd) AS DOUBLE)) AS c0,
            0 AS c1, 0 AS c2, 0 AS c3, 0 AS c4, 0 AS c5, 0 AS c6, 0 AS c7, 0 AS c8, 0 AS c9,
            0 AS c10, 0 AS c11, 0 AS c12, 0 AS c13, 0 AS c14, 0 AS c15, 0 AS c16, 0 AS c17,
            0 AS c18, 0 AS c19, 0 AS c20, 0 AS c21, 0 AS c22, 0 AS c23, 0 AS c24
        FROM v_event_{project_id}
        WHERE "$part_event" = 'facebook_ad_level_data_by_platform'
          AND "$part_date" >= '2026-01-01'
          AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{fb_cut}'
          AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
          AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
        GROUP BY 1, 2
        UNION ALL
        SELECT
            ta_date_trunc('day', "#event_time", 1) AS "$__Date_Time",
            {os_cost_abs_unity} AS "$__OS",
            SUM(CAST(coalesce("spend", spend) AS DOUBLE)) AS c0,
            0 AS c1, 0 AS c2, 0 AS c3, 0 AS c4, 0 AS c5, 0 AS c6, 0 AS c7, 0 AS c8, 0 AS c9,
            0 AS c10, 0 AS c11, 0 AS c12, 0 AS c13, 0 AS c14, 0 AS c15, 0 AS c16, 0 AS c17,
            0 AS c18, 0 AS c19, 0 AS c20, 0 AS c21, 0 AS c22, 0 AS c23, 0 AS c24
        FROM v_event_{project_id}
        WHERE "$part_event" = 'unity_ads_api_data'
          AND "$part_date" >= '2026-01-01'
          AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{unity_cut}'
          AND ta_date_trunc('day', "#event_time", 1) >= TIMESTAMP '{start_date}'
          AND ta_date_trunc('day', "#event_time", 1) < date_add('day', 1, TIMESTAMP '{end_date}')
        GROUP BY 1, 2
        UNION ALL
        SELECT
            ta_date_trunc('day', ta_u.inst_t, 1) AS "$__Date_Time",
            ta_u.os_display AS "$__OS",
            0 AS c0,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'first_start_up', ta_ev."#user_id"))) AS DOUBLE) AS c1,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '10', ta_ev."#user_id"))) AS DOUBLE) AS c2,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '20', ta_ev."#user_id"))) AS DOUBLE) AS c3,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev."#user_id"))) AS DOUBLE) AS c4,
            CAST(SUM(CAST(IF(ta_ev."$part_event" = 'applovin_ad_revenue_impression_level' AND ta_ev.ad_format IN ('REWARDED','INTER'), ta_ev.revenue) AS DOUBLE)) AS DOUBLE) AS c5,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev."#user_id"))) AS DOUBLE) AS c6,
            CAST(SUM(CAST(IF(ta_ev."$part_event" = 'iap_recharge_succeed', ta_ev.iap_product_currency) AS DOUBLE)) AS DOUBLE) AS c7,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '30', ta_ev."#user_id"))) AS DOUBLE) AS c8,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '40', ta_ev."#user_id"))) AS DOUBLE) AS c9,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '50', ta_ev."#user_id"))) AS DOUBLE) AS c10,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '60', ta_ev."#user_id"))) AS DOUBLE) AS c11,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '70', ta_ev."#user_id"))) AS DOUBLE) AS c12,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '80', ta_ev."#user_id"))) AS DOUBLE) AS c13,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '90', ta_ev."#user_id"))) AS DOUBLE) AS c14,
            CAST(COUNT(DISTINCT (IF(ta_ev."$part_event" = 'level_start' AND ta_ev.level_id = '100', ta_ev."#user_id"))) AS DOUBLE) AS c15,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm IS NULL, ta_ev."#user_id"))) AS DOUBLE) AS c16,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 0 AND ta_u.ecpm < 100, ta_ev."#user_id"))) AS DOUBLE) AS c17,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 100 AND ta_u.ecpm < 200, ta_ev."#user_id"))) AS DOUBLE) AS c18,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 200 AND ta_u.ecpm < 300, ta_ev."#user_id"))) AS DOUBLE) AS c19,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 300 AND ta_u.ecpm < 400, ta_ev."#user_id"))) AS DOUBLE) AS c20,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 400 AND ta_u.ecpm < 500, ta_ev."#user_id"))) AS DOUBLE) AS c21,
            CAST(COUNT(DISTINCT (IF(ta_u.ecpm >= 500, ta_ev."#user_id"))) AS DOUBLE) AS c22,
            CAST(COUNT(IF(ta_ev."$part_event" = 'iap_recharge_succeed', 1)) AS DOUBLE) AS c23,
            CAST(COUNT(DISTINCT (IF(ta_u.first_iap_t IS NOT NULL AND ta_date_trunc('day', ta_u.first_iap_t, 1) = ta_date_trunc('day', ta_u.inst_t, 1), ta_ev."#user_id"))) AS DOUBLE) AS c24
        FROM (
            SELECT "#user_id", "$part_event", "level_id", "ad_format", "revenue", "iap_product_currency", "#app_version"
            FROM v_event_{project_id}
            WHERE "$part_event" IN ('first_start_up', 'level_start', 'applovin_ad_revenue_impression_level', 'iap_recharge_succeed')
              AND "$part_date" >= '2026-01-01'
              AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce("#zone_offset", 0) AS INTEGER), "#event_time"), 1) >= TIMESTAMP '{start_date}'
              AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce("#zone_offset", 0) AS INTEGER), "#event_time"), 1) < date_add('day', 1, TIMESTAMP '{today_str}')
        ) ta_ev
        INNER JOIN (
            SELECT cohort."#user_id", cohort.v_first, cohort.inst_t, cohort.ecpm, cohort.os_display, fi.first_iap_t
            FROM (
                SELECT ev."#user_id", u."app_version_first" AS v_first,
                       min(date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time")) AS inst_t,
                       arbitrary(u.first_rv_ecpm) AS ecpm,
                       CASE WHEN lower(COALESCE(CAST(arbitrary(ev."#os") AS VARCHAR), '')) IN ('ios', 'apple') THEN 'iOS'
                            WHEN lower(COALESCE(CAST(arbitrary(ev."#os") AS VARCHAR), '')) IN ('android') THEN 'Android'
                            ELSE 'Unknown' END AS os_display
                FROM v_event_{project_id} ev
                LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
                WHERE ev."$part_event" = 'first_start_up'
                  AND ev."$part_date" >= '2026-01-01'
                  AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) >= TIMESTAMP '{start_date}'
                  AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) < date_add('day', 1, TIMESTAMP '{end_date}')
                  AND u."is_test" = false
                  AND coalesce(CAST(u."#account_id" AS VARCHAR), '') NOT IN (
                      '86122677072314368', '85632127382601728', '85631822439923712'
                  )
                GROUP BY 1, 2
            ) cohort
            LEFT JOIN (
                SELECT i."#user_id", u2."app_version_first" AS v_first,
                       min(date_add('hour', -8 - CAST(coalesce(i."#zone_offset", 0) AS INTEGER), i."#event_time")) AS first_iap_t
                FROM v_event_{project_id} i
                LEFT JOIN v_user_{project_id} u2 ON i."#user_id" = u2."#user_id"
                WHERE i."$part_event" = 'iap_recharge_succeed'
                  AND i."$part_date" >= '2026-01-01'
                  AND i."#app_version" = u2."app_version_first"
                GROUP BY 1, 2
            ) fi ON cohort."#user_id" = fi."#user_id" AND cohort.v_first = fi.v_first
        ) ta_u ON ta_ev."#user_id" = ta_u."#user_id"
        WHERE ta_ev."#app_version" = ta_u.v_first
        GROUP BY 1, 2
    )
    WHERE "$__Date_Time" >= TIMESTAMP '{start_date}' AND "$__Date_Time" < date_add('day', 1, TIMESTAMP '{end_date}')
    GROUP BY format_datetime("$__Date_Time", 'yyyy-MM-dd'), "$__OS"
)
ORDER BY "Date" DESC, "OS" ASC
"""

    @staticmethod
    def get_empty_result_diagnosis_sql(project_id, start_date, end_date):
        """
        主查询解析为空时由 app 调用：轻量统计 cohort 窗口内 first_start_up 人数与安装日范围，
        过滤条件与 get_cohort_fine_grain_sql 中 cohort 子查询一致，便于排查是否无用户或被账号/测试过滤。
        """
        return f"""
/* sessionProperties: {{"ignore_downstream_preferences":"true"}} */
SELECT
    count(DISTINCT ev."#user_id") AS cohort_first_start_up_uv,
    min(ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1)) AS min_inst_day,
    max(ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1)) AS max_inst_day
FROM v_event_{project_id} ev
LEFT JOIN v_user_{project_id} u ON ev."#user_id" = u."#user_id"
WHERE ev."$part_event" = 'first_start_up'
  AND ev."$part_date" >= '2026-01-01'
  AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) >= TIMESTAMP '{start_date}'
  AND ta_date_trunc('day', date_add('hour', -8 - CAST(coalesce(ev."#zone_offset", 0) AS INTEGER), ev."#event_time"), 1) < date_add('day', 1, TIMESTAMP '{end_date}')
  AND u."is_test" = false
  AND coalesce(CAST(u."#account_id" AS VARCHAR), '') NOT IN (
      '86122677072314368', '85632127382601728', '85631822439923712'
  )
"""

    @staticmethod
    def get_advertising_report_sql(project_id, start_date, end_date, dimension="campaign_name"):
        """广告层级：SQL 固定输出计划/组/创意三维；dimension 参数仅保留兼容，不参与 SQL。"""
        return AdAnalysis.get_cohort_fine_grain_sql(project_id, start_date, end_date)
