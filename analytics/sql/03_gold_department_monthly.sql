-- gold_department_monthly : department x month with one row per department in
-- every month.  Department occupancy uses hospital-level bed-snapshot occupancy
-- as a documented proxy because bed_snapshots carry a ward but no department_id.
WITH depts AS (
    SELECT d.hospital_id, d.department_id, d.department_name, d.specialty_id,
           s.specialty_name
    FROM dim_department d
    LEFT JOIN dim_specialty s ON d.specialty_id = s.specialty_id
),
grid AS (
    SELECT de.hospital_id, de.department_id, de.department_name, de.specialty_id,
           de.specialty_name, m.month
    FROM depts de CROSS JOIN dim_month m
),
pat AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', arrival_datetime)::DATE AS month,
           COUNT(DISTINCT patient_id) AS patients
    FROM silver_encounters
    WHERE arrival_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
enc AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', arrival_datetime)::DATE AS month,
           COUNT(*) AS encounters
    FROM silver_encounters
    WHERE arrival_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
adm AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', admission_datetime)::DATE AS month,
           COUNT(*) AS admissions
    FROM silver_admissions
    WHERE admission_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
apt AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', appointment_date)::DATE AS month,
           COUNT(*) AS appointments,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('no-show', 'no show', 'noshow')) AS no_shows,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed,
           AVG(waiting_minutes) AS avg_wait_minutes
    FROM silver_appointments
    WHERE appointment_date IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
occ AS (
    SELECT hospital_id, DATE_TRUNC('month', snapshot_datetime)::DATE AS month,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'occupied'
                              OR COALESCE(occupied_flag, FALSE)) AS occ_days,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) <> 'blocked'
                              AND NOT COALESCE(blocked_flag, FALSE)) AS avail_days
    FROM silver_bed_snapshots
    WHERE snapshot_datetime IS NOT NULL
    GROUP BY 1, 2
),
los AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', discharge_datetime)::DATE AS month,
           AVG(los_days) AS avg_los_days
    FROM silver_admissions
    WHERE discharge_datetime IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
rev AS (
    SELECT e.hospital_id, e.department_id, DATE_TRUNC('month', i.invoice_date)::DATE AS month,
           SUM(i.net_amount) AS revenue
    FROM silver_invoices i
    JOIN silver_encounters e ON i.encounter_id = e.encounter_id
    WHERE i.invoice_date IS NOT NULL AND e.department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
lab AS (
    SELECT o.hospital_id, o.ordering_department AS department_id,
           DATE_TRUNC('month', o.ordered_at)::DATE AS month,
           COUNT(*) AS lab_orders,
           AVG(r.tat_minutes) AS avg_lab_tat_minutes
    FROM silver_lab_orders o
    LEFT JOIN silver_lab_results r ON r.lab_order_id = o.lab_order_id
    WHERE o.ordered_at IS NOT NULL
    GROUP BY 1, 2, 3
),
den AS (
    SELECT e.hospital_id, e.department_id, DATE_TRUNC('month', c.claim_date)::DATE AS month,
           COUNT(*) FILTER (WHERE LOWER(c.status) = 'denied') AS denied,
           COUNT(*) FILTER (WHERE LOWER(c.status) IN ('approved', 'denied')) AS adjudicated
    FROM silver_claims c
    JOIN silver_invoices i ON c.invoice_id = i.invoice_id
    JOIN silver_encounters e ON i.encounter_id = e.encounter_id
    WHERE c.claim_date IS NOT NULL AND e.department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
fb AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', visit_date)::DATE AS month,
           AVG(rating) AS avg_satisfaction
    FROM silver_feedback
    WHERE visit_date IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
),
inc AS (
    SELECT hospital_id, department_id, DATE_TRUNC('month', incident_date)::DATE AS month,
           COUNT(*) AS incidents_count
    FROM silver_incidents
    WHERE incident_date IS NOT NULL AND department_id IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.department_id, g.department_name, g.specialty_id,
       g.specialty_name, g.month,
       CAST(COALESCE(p.patients, 0) AS INTEGER) AS patients,
       CAST(COALESCE(e.encounters, 0) AS INTEGER) AS encounters,
       CAST(COALESCE(a.admissions, 0) AS INTEGER) AS admissions,
       CAST(COALESCE(ap.appointments, 0) AS INTEGER) AS appointments,
       ROUND(100.0 * ap.no_shows / NULLIF(ap.completed + ap.no_shows, 0), 2) AS no_show_rate,
       ROUND(ap.avg_wait_minutes, 2) AS avg_wait_minutes,
       ROUND(100.0 * o.occ_days / NULLIF(o.avail_days, 0), 2) AS occupancy_rate,
       ROUND(l.avg_los_days, 2) AS avg_los_days,
       COALESCE(r.revenue, 0.0) AS revenue,
       CAST(COALESCE(lb.lab_orders, 0) AS INTEGER) AS lab_orders,
       ROUND(lb.avg_lab_tat_minutes, 2) AS avg_lab_tat_minutes,
       ROUND(100.0 * dn.denied / NULLIF(dn.adjudicated, 0), 2) AS denial_rate,
       ROUND(f.avg_satisfaction, 2) AS avg_satisfaction,
       CAST(COALESCE(i.incidents_count, 0) AS INTEGER) AS incidents_count
FROM grid g
LEFT JOIN pat p ON p.hospital_id = g.hospital_id AND p.department_id = g.department_id AND p.month = g.month
LEFT JOIN enc e ON e.hospital_id = g.hospital_id AND e.department_id = g.department_id AND e.month = g.month
LEFT JOIN adm a ON a.hospital_id = g.hospital_id AND a.department_id = g.department_id AND a.month = g.month
LEFT JOIN apt ap ON ap.hospital_id = g.hospital_id AND ap.department_id = g.department_id AND ap.month = g.month
LEFT JOIN occ o ON o.hospital_id = g.hospital_id AND o.month = g.month
LEFT JOIN los l ON l.hospital_id = g.hospital_id AND l.department_id = g.department_id AND l.month = g.month
LEFT JOIN rev r ON r.hospital_id = g.hospital_id AND r.department_id = g.department_id AND r.month = g.month
LEFT JOIN lab lb ON lb.hospital_id = g.hospital_id AND lb.department_id = g.department_id AND lb.month = g.month
LEFT JOIN den dn ON dn.hospital_id = g.hospital_id AND dn.department_id = g.department_id AND dn.month = g.month
LEFT JOIN fb f ON f.hospital_id = g.hospital_id AND f.department_id = g.department_id AND f.month = g.month
LEFT JOIN inc i ON i.hospital_id = g.hospital_id AND i.department_id = g.department_id AND i.month = g.month
ORDER BY g.hospital_id, g.department_id, g.month;
