-- gold_workforce : staffing by hospital-department-month.
-- coverage_pct = worked / scheduled hours, capped at 100 (overtime reported
-- separately); absence_rate uses attendance events within the same shifts.
WITH grid AS (
    SELECT d.hospital_id, d.department_id, m.month
    FROM dim_department d CROSS JOIN dim_month m
),
shifts AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', shift_date)::DATE AS month,
           COUNT(DISTINCT staff_id) AS headcount,
           SUM(scheduled_hours) AS scheduled_hours,
           SUM(actual_hours) AS worked_hours,
           SUM(overtime_hours) AS overtime_hours
    FROM silver_shifts
    WHERE shift_date IS NOT NULL
    GROUP BY 1, 2, 3
),
att AS (
    SELECT s.hospital_id, s.department_id, DATE_TRUNC('month', s.shift_date)::DATE AS month,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(a.status, '')) IN ('absent', 'leave')) AS absent,
           COUNT(*) AS attendance_events
    FROM silver_attendance a
    JOIN silver_shifts s ON a.shift_id = s.shift_id
    WHERE s.shift_date IS NOT NULL
    GROUP BY 1, 2, 3
),
cost AS (
    SELECT s.hospital_id, s.department_id, DATE_TRUNC('month', s.shift_date)::DATE AS month,
           SUM(COALESCE(s.actual_hours, 0) * COALESCE(st.hourly_rate, 0)) AS workforce_cost
    FROM silver_shifts s
    LEFT JOIN dim_staff st ON s.staff_id = st.staff_id
    WHERE s.shift_date IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.department_id, g.month,
       CAST(COALESCE(s.headcount, 0) AS INTEGER) AS headcount,
       COALESCE(s.scheduled_hours, 0.0) AS scheduled_hours,
       COALESCE(s.worked_hours, 0.0) AS worked_hours,
       COALESCE(s.overtime_hours, 0.0) AS overtime_hours,
       ROUND(100.0 * a.absent / NULLIF(a.attendance_events, 0), 2) AS absence_rate,
       CASE WHEN s.scheduled_hours IS NULL OR s.scheduled_hours = 0 THEN NULL
            ELSE ROUND(LEAST(100.0, 100.0 * COALESCE(s.worked_hours, 0) / s.scheduled_hours), 2)
       END AS coverage_pct,
       COALESCE(c.workforce_cost, 0.0) AS workforce_cost
FROM grid g
LEFT JOIN shifts s ON s.hospital_id = g.hospital_id AND s.department_id = g.department_id AND s.month = g.month
LEFT JOIN att a ON a.hospital_id = g.hospital_id AND a.department_id = g.department_id AND a.month = g.month
LEFT JOIN cost c ON c.hospital_id = g.hospital_id AND c.department_id = g.department_id AND c.month = g.month
ORDER BY g.hospital_id, g.department_id, g.month;
