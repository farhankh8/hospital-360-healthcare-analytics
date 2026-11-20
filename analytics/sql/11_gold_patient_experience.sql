-- gold_patient_experience : satisfaction, NPS and complaints by hospital-department-month.
-- satisfaction_pct = AVG(rating)/5*100 ; nps = (promoters - detractors)/total*100
-- with promoters nps_score >= 9 and detractors nps_score <= 6 (range -100..100).
WITH grid AS (
    SELECT d.hospital_id, d.department_id, m.month
    FROM dim_department d CROSS JOIN dim_month m
),
fb AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', visit_date)::DATE AS month,
           COUNT(*) AS feedback_count,
           AVG(rating) AS avg_rating,
           COUNT(*) FILTER (WHERE nps_score >= 9) AS promoters,
           COUNT(*) FILTER (WHERE nps_score <= 6) AS detractors,
           COUNT(*) FILTER (WHERE complaint_flag) AS complaints,
           AVG(resolution_days) FILTER (WHERE complaint_flag) AS complaint_resolution_days
    FROM silver_feedback
    WHERE visit_date IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.department_id, g.month,
       CAST(COALESCE(f.feedback_count, 0) AS INTEGER) AS feedback_count,
       ROUND(f.avg_rating, 2) AS avg_rating,
       ROUND(100.0 * f.avg_rating / 5.0, 2) AS satisfaction_pct,
       CAST(COALESCE(f.promoters, 0) AS INTEGER) AS promoters,
       CAST(COALESCE(f.detractors, 0) AS INTEGER) AS detractors,
       ROUND(100.0 * (f.promoters - f.detractors)
             / NULLIF(f.feedback_count, 0), 2) AS nps,
       CAST(COALESCE(f.complaints, 0) AS INTEGER) AS complaints,
       ROUND(f.complaint_resolution_days, 2) AS complaint_resolution_days
FROM grid g
LEFT JOIN fb f ON f.hospital_id = g.hospital_id AND f.department_id = g.department_id AND f.month = g.month
ORDER BY g.hospital_id, g.department_id, g.month;
