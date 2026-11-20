-- gold_patient_access : appointment access/attendance at hospital-department-month.
-- no_show_rate excludes cancelled appointments by construction.
WITH grid AS (
    SELECT d.hospital_id, d.department_id, m.month
    FROM dim_department d CROSS JOIN dim_month m
),
apt AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', appointment_date)::DATE AS month,
           COUNT(*) AS scheduled,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('cancelled', 'canceled')) AS cancelled,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('no-show', 'no show', 'noshow')) AS no_shows,
           AVG(waiting_minutes) AS avg_wait_minutes,
           AVG(lead_days) AS avg_lead_days,
           COUNT(*) FILTER (WHERE COALESCE(lead_days, -1) = 0) AS same_day,
           COUNT(*) FILTER (WHERE rescheduled_flag) AS rescheduled
    FROM silver_appointments
    WHERE appointment_date IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.department_id, g.month,
       CAST(COALESCE(a.scheduled, 0) AS INTEGER) AS scheduled,
       CAST(COALESCE(a.completed, 0) AS INTEGER) AS completed,
       CAST(COALESCE(a.cancelled, 0) AS INTEGER) AS cancelled,
       CAST(COALESCE(a.no_shows, 0) AS INTEGER) AS no_shows,
       ROUND(100.0 * a.no_shows / NULLIF(a.completed + a.no_shows, 0), 2) AS no_show_rate,
       ROUND(a.avg_wait_minutes, 2) AS avg_wait_minutes,
       ROUND(a.avg_lead_days, 2) AS avg_lead_days,
       ROUND(100.0 * a.same_day / NULLIF(a.scheduled, 0), 2) AS same_day_pct,
       ROUND(100.0 * a.rescheduled / NULLIF(a.scheduled, 0), 2) AS reschedule_rate
FROM grid g
LEFT JOIN apt a ON a.hospital_id = g.hospital_id AND a.department_id = g.department_id AND a.month = g.month
ORDER BY g.hospital_id, g.department_id, g.month;
