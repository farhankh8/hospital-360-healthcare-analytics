-- gold_quality_safety : incidents and readmissions by hospital-department-month.
-- incident_rate is incidents per 100 encounters; readmission_rate is
-- readmissions per discharge in the same hospital/department/month.
WITH grid AS (
    SELECT d.hospital_id, d.department_id, m.month
    FROM dim_department d CROSS JOIN dim_month m
),
inc AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', incident_date)::DATE AS month,
           COUNT(*) AS incidents,
           COUNT(*) FILTER (WHERE LOWER(category) = 'fall') AS falls,
           COUNT(*) FILTER (WHERE LOWER(category) = 'medication') AS medication_incidents,
           COUNT(*) FILTER (WHERE LOWER(category) = 'infection') AS infection_incidents,
           COUNT(*) FILTER (WHERE LOWER(severity) = 'critical') AS critical_incidents,
           COUNT(*) FILTER (WHERE investigation_complete_flag) AS investigations_complete,
           AVG(investigation_days) AS avg_investigation_days
    FROM silver_incidents
    WHERE incident_date IS NOT NULL
    GROUP BY 1, 2, 3
),
denom AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', arrival_datetime)::DATE AS month,
           COUNT(*) AS encounters
    FROM silver_encounters
    WHERE arrival_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
readm AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', discharge_datetime)::DATE AS month,
           COUNT(*) FILTER (WHERE readmission_flag) AS readmissions,
           COUNT(*) AS discharges
    FROM silver_admissions
    WHERE discharge_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.department_id, g.month,
       CAST(COALESCE(i.incidents, 0) AS INTEGER) AS incidents,
       ROUND(100.0 * i.incidents / NULLIF(d.encounters, 0), 2) AS incident_rate,
       CAST(COALESCE(i.falls, 0) AS INTEGER) AS falls,
       CAST(COALESCE(i.medication_incidents, 0) AS INTEGER) AS medication_incidents,
       CAST(COALESCE(i.infection_incidents, 0) AS INTEGER) AS infection_incidents,
       CAST(COALESCE(i.critical_incidents, 0) AS INTEGER) AS critical_incidents,
       ROUND(100.0 * i.investigations_complete / NULLIF(i.incidents, 0), 2) AS investigation_completion_rate,
       ROUND(i.avg_investigation_days, 2) AS avg_investigation_days,
       ROUND(100.0 * r.readmissions / NULLIF(r.discharges, 0), 2) AS readmission_rate
FROM grid g
LEFT JOIN inc i ON i.hospital_id = g.hospital_id AND i.department_id = g.department_id AND i.month = g.month
LEFT JOIN denom d ON d.hospital_id = g.hospital_id AND d.department_id = g.department_id AND d.month = g.month
LEFT JOIN readm r ON r.hospital_id = g.hospital_id AND r.department_id = g.department_id AND r.month = g.month
ORDER BY g.hospital_id, g.department_id, g.month;
