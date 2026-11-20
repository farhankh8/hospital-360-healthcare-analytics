-- gold_lab_performance : laboratory test x hospital x month.
-- sla_rate / delayed are measured against dim_lab_test.sla_minutes.
WITH grid AS (
    SELECT h.hospital_id, t.test_code, t.test_name, m.month
    FROM dim_hospital h CROSS JOIN dim_lab_test t CROSS JOIN dim_month m
    WHERE h.hospital_id IN ('H01','H02','H03','H04','H05','H06','H07','H08','H09','H10')
),
orders AS (
    SELECT hospital_id, test_code, DATE_TRUNC('month', ordered_at)::DATE AS month,
           COUNT(*) AS orders,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed,
           COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending,
           COUNT(*) FILTER (WHERE LOWER(status) = 'cancelled') AS cancelled
    FROM silver_lab_orders
    WHERE ordered_at IS NOT NULL
    GROUP BY 1, 2, 3
),
res AS (
    SELECT o.hospital_id, o.test_code, DATE_TRUNC('month', o.ordered_at)::DATE AS month,
           AVG(r.tat_minutes) AS avg_tat_minutes,
           MEDIAN(r.tat_minutes) AS median_tat_minutes,
           COUNT(*) FILTER (WHERE r.tat_minutes IS NOT NULL AND s.sla_minutes IS NOT NULL
                              AND r.tat_minutes <= s.sla_minutes) AS sla_met,
           COUNT(*) FILTER (WHERE r.tat_minutes IS NOT NULL AND s.sla_minutes IS NOT NULL
                              AND r.tat_minutes > s.sla_minutes) AS delayed,
           COUNT(*) FILTER (WHERE r.is_critical) AS critical,
           COUNT(*) FILTER (WHERE r.tat_minutes IS NOT NULL) AS timed
    FROM silver_lab_results r
    JOIN silver_lab_orders o ON r.lab_order_id = o.lab_order_id
    LEFT JOIN dim_lab_test s ON o.test_code = s.test_code
    WHERE o.ordered_at IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.test_code, g.test_name, g.month,
       CAST(COALESCE(o.orders, 0) AS INTEGER) AS orders,
       CAST(COALESCE(o.completed, 0) AS INTEGER) AS completed,
       CAST(COALESCE(o.pending, 0) AS INTEGER) AS pending,
       CAST(COALESCE(o.cancelled, 0) AS INTEGER) AS cancelled,
       ROUND(r.avg_tat_minutes, 2) AS avg_tat_minutes,
       ROUND(r.median_tat_minutes, 2) AS median_tat_minutes,
       ROUND(100.0 * r.sla_met / NULLIF(r.timed, 0), 2) AS sla_rate,
       CAST(COALESCE(r.delayed, 0) AS INTEGER) AS delayed,
       CAST(COALESCE(r.critical, 0) AS INTEGER) AS critical
FROM grid g
LEFT JOIN orders o ON o.hospital_id = g.hospital_id AND o.test_code = g.test_code AND o.month = g.month
LEFT JOIN res r ON r.hospital_id = g.hospital_id AND r.test_code = g.test_code AND r.month = g.month
ORDER BY g.hospital_id, g.test_code, g.month;
