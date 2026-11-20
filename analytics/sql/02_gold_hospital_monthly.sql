-- gold_hospital_monthly : the main workhorse. 10 hospitals x 24 months = 240 rows.
-- Left joins onto the grid keep every chart continuous; counts become 0, rates
-- become NULL when the denominator is zero (never a fabricated zero).
WITH grid AS (
    SELECT h.hospital_id, h.hospital_name, m.month
    FROM dim_hospital h
    CROSS JOIN dim_month m
    WHERE h.hospital_id IN ('H01','H02','H03','H04','H05','H06','H07','H08','H09','H10')
),
pat AS (
    SELECT hospital_id, DATE_TRUNC('month', arrival_datetime)::DATE AS month,
           COUNT(DISTINCT patient_id) AS patients
    FROM silver_encounters
    WHERE hospital_id IS NOT NULL AND arrival_datetime IS NOT NULL
    GROUP BY 1, 2
),
enc AS (
    SELECT hospital_id, DATE_TRUNC('month', arrival_datetime)::DATE AS month,
           COUNT(*) AS encounters
    FROM silver_encounters
    WHERE arrival_datetime IS NOT NULL
    GROUP BY 1, 2
),
adm AS (
    SELECT hospital_id, DATE_TRUNC('month', admission_datetime)::DATE AS month,
           COUNT(*) AS admissions
    FROM silver_admissions
    WHERE admission_datetime IS NOT NULL
    GROUP BY 1, 2
),
dis AS (
    SELECT hospital_id, DATE_TRUNC('month', discharge_datetime)::DATE AS month,
           COUNT(*) AS discharges,
           COUNT(*) FILTER (WHERE readmission_flag) AS readmissions,
           AVG(los_days) AS avg_los_days
    FROM silver_admissions
    WHERE discharge_datetime IS NOT NULL
    GROUP BY 1, 2
),
apt AS (
    SELECT hospital_id, DATE_TRUNC('month', appointment_date)::DATE AS month,
           COUNT(*) AS appointments,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed_appointments,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('cancelled', 'canceled')) AS cancelled_appointments,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('no-show', 'no show', 'noshow')) AS no_show_appointments,
           AVG(waiting_minutes) AS avg_wait_minutes
    FROM silver_appointments
    WHERE appointment_date IS NOT NULL
    GROUP BY 1, 2
),
beds AS (
    SELECT hospital_id, DATE_TRUNC('month', snapshot_datetime)::DATE AS month,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'occupied'
                              OR COALESCE(occupied_flag, FALSE)) AS occupied_bed_days,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) <> 'blocked'
                              AND NOT COALESCE(blocked_flag, FALSE)) AS available_bed_days
    FROM silver_bed_snapshots
    WHERE snapshot_datetime IS NOT NULL
    GROUP BY 1, 2
),
fin AS (
    SELECT hospital_id, DATE_TRUNC('month', invoice_date)::DATE AS month,
           SUM(gross_amount) AS gross_revenue,
           SUM(net_amount) AS net_revenue,
           SUM(balance_amount) AS outstanding_balance
    FROM silver_invoices
    WHERE invoice_date IS NOT NULL
    GROUP BY 1, 2
),
cash AS (
    SELECT i.hospital_id, DATE_TRUNC('month', p.payment_date)::DATE AS month,
           SUM(CASE WHEN LOWER(COALESCE(p.payment_type, '')) = 'refund'
                    THEN -ABS(COALESCE(p.amount, 0)) ELSE COALESCE(p.amount, 0) END) AS collections
    FROM silver_payments p
    JOIN silver_invoices i ON p.invoice_id = i.invoice_id
    WHERE p.payment_date IS NOT NULL AND LOWER(COALESCE(p.status, '')) = 'cleared'
    GROUP BY 1, 2
),
lab AS (
    SELECT hospital_id, DATE_TRUNC('month', ordered_at)::DATE AS month,
           COUNT(*) AS lab_orders,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed_lab_tests
    FROM silver_lab_orders
    WHERE ordered_at IS NOT NULL
    GROUP BY 1, 2
),
tat AS (
    SELECT o.hospital_id, DATE_TRUNC('month', o.ordered_at)::DATE AS month,
           AVG(r.tat_minutes) AS avg_lab_tat_minutes,
           COUNT(*) FILTER (WHERE r.tat_minutes IS NOT NULL
                              AND r.tat_minutes <= t.sla_minutes) AS sla_met,
           COUNT(*) FILTER (WHERE r.tat_minutes IS NOT NULL) AS timed_results
    FROM silver_lab_results r
    JOIN silver_lab_orders o ON r.lab_order_id = o.lab_order_id
    LEFT JOIN dim_lab_test t ON r.test_code = t.test_code
    WHERE o.ordered_at IS NOT NULL
    GROUP BY 1, 2
),
clm AS (
    SELECT hospital_id, DATE_TRUNC('month', claim_date)::DATE AS month,
           COUNT(*) AS claims_submitted,
           COUNT(*) FILTER (WHERE LOWER(status) = 'approved') AS approved,
           COUNT(*) FILTER (WHERE LOWER(status) = 'denied') AS claims_denied
    FROM silver_claims
    WHERE claim_date IS NOT NULL
    GROUP BY 1, 2
),
fb AS (
    SELECT hospital_id, DATE_TRUNC('month', visit_date)::DATE AS month,
           COUNT(*) AS feedback_count,
           AVG(rating) AS avg_satisfaction,
           COUNT(*) FILTER (WHERE complaint_flag) AS complaint_count
    FROM silver_feedback
    WHERE visit_date IS NOT NULL
    GROUP BY 1, 2
),
inc AS (
    SELECT hospital_id, DATE_TRUNC('month', incident_date)::DATE AS month,
           COUNT(*) AS incidents_count
    FROM silver_incidents
    WHERE incident_date IS NOT NULL
    GROUP BY 1, 2
),
wrk AS (
    SELECT hospital_id, DATE_TRUNC('month', shift_date)::DATE AS month,
           SUM(scheduled_hours) AS scheduled_hours,
           SUM(actual_hours) AS worked_hours,
           SUM(overtime_hours) AS overtime_hours
    FROM silver_shifts
    WHERE shift_date IS NOT NULL
    GROUP BY 1, 2
),
inv AS (
    SELECT hospital_id, DATE_TRUNC('month', movement_date)::DATE AS month,
           COUNT(DISTINCT item_id) FILTER (WHERE LOWER(movement_type) = 'issue') AS stockouts,
           SUM(CASE WHEN quantity > 0 THEN quantity * COALESCE(unit_cost, 0) ELSE 0 END) AS inventory_value
    FROM silver_inventory_movements
    WHERE movement_date IS NOT NULL
    GROUP BY 1, 2
)
SELECT g.hospital_id, g.hospital_name, g.month,
       CAST(COALESCE(p.patients, 0) AS INTEGER) AS patients,
       CAST(COALESCE(e.encounters, 0) AS INTEGER) AS encounters,
       CAST(COALESCE(a.admissions, 0) AS INTEGER) AS admissions,
       CAST(COALESCE(d.discharges, 0) AS INTEGER) AS discharges,
       CAST(COALESCE(ap.appointments, 0) AS INTEGER) AS appointments,
       CAST(COALESCE(ap.completed_appointments, 0) AS INTEGER) AS completed_appointments,
       CAST(COALESCE(ap.cancelled_appointments, 0) AS INTEGER) AS cancelled_appointments,
       CAST(COALESCE(ap.no_show_appointments, 0) AS INTEGER) AS no_show_appointments,
       ROUND(100.0 * ap.no_show_appointments
             / NULLIF(ap.completed_appointments + ap.no_show_appointments, 0), 2) AS no_show_rate,
       ROUND(ap.avg_wait_minutes, 2) AS avg_wait_minutes,
       COALESCE(b.occupied_bed_days, 0.0) AS occupied_bed_days,
       COALESCE(b.available_bed_days, 0.0) AS available_bed_days,
       ROUND(100.0 * b.occupied_bed_days / NULLIF(b.available_bed_days, 0), 2) AS occupancy_rate,
       ROUND(d.avg_los_days, 2) AS avg_los_days,
       CAST(COALESCE(d.readmissions, 0) AS INTEGER) AS readmissions,
       ROUND(100.0 * d.readmissions / NULLIF(d.discharges, 0), 2) AS readmission_rate,
       COALESCE(f.gross_revenue, 0.0) AS gross_revenue,
       COALESCE(f.net_revenue, 0.0) AS net_revenue,
       COALESCE(c.collections, 0.0) AS collections,
       COALESCE(f.outstanding_balance, 0.0) AS outstanding_balance,
       -- Collections may settle invoices issued in earlier months; cap the
       -- period rate at 100%. CASE preserves NULL when the denominator is 0
       -- (DuckDB LEAST/GREATEST would otherwise turn NULL into 100).
       CASE WHEN f.net_revenue IS NULL OR f.net_revenue = 0 THEN NULL
            ELSE ROUND(GREATEST(0.0, LEAST(100.0,
                   100.0 * COALESCE(c.collections, 0) / f.net_revenue)), 2)
       END AS collection_rate,
       CAST(COALESCE(l.lab_orders, 0) AS INTEGER) AS lab_orders,
       CAST(COALESCE(l.completed_lab_tests, 0) AS INTEGER) AS completed_lab_tests,
       ROUND(t.avg_lab_tat_minutes, 2) AS avg_lab_tat_minutes,
       ROUND(100.0 * t.sla_met / NULLIF(t.timed_results, 0), 2) AS lab_sla_rate,
       CAST(COALESCE(cl.claims_submitted, 0) AS INTEGER) AS claims_submitted,
       CAST(COALESCE(cl.claims_denied, 0) AS INTEGER) AS claims_denied,
       ROUND(100.0 * cl.claims_denied / NULLIF(cl.approved + cl.claims_denied, 0), 2) AS denial_rate,
       CAST(COALESCE(fb.feedback_count, 0) AS INTEGER) AS feedback_count,
       ROUND(fb.avg_satisfaction, 2) AS avg_satisfaction,
       CAST(COALESCE(fb.complaint_count, 0) AS INTEGER) AS complaint_count,
       CAST(COALESCE(i.incidents_count, 0) AS INTEGER) AS incidents_count,
       COALESCE(w.scheduled_hours, 0.0) AS scheduled_hours,
       COALESCE(w.worked_hours, 0.0) AS worked_hours,
       COALESCE(w.overtime_hours, 0.0) AS overtime_hours,
       CAST(COALESCE(iv.stockouts, 0) AS INTEGER) AS stockouts,
       COALESCE(iv.inventory_value, 0.0) AS inventory_value
FROM grid g
LEFT JOIN pat p ON p.hospital_id = g.hospital_id AND p.month = g.month
LEFT JOIN enc e ON e.hospital_id = g.hospital_id AND e.month = g.month
LEFT JOIN adm a ON a.hospital_id = g.hospital_id AND a.month = g.month
LEFT JOIN dis d ON d.hospital_id = g.hospital_id AND d.month = g.month
LEFT JOIN apt ap ON ap.hospital_id = g.hospital_id AND ap.month = g.month
LEFT JOIN beds b ON b.hospital_id = g.hospital_id AND b.month = g.month
LEFT JOIN fin f ON f.hospital_id = g.hospital_id AND f.month = g.month
LEFT JOIN cash c ON c.hospital_id = g.hospital_id AND c.month = g.month
LEFT JOIN lab l ON l.hospital_id = g.hospital_id AND l.month = g.month
LEFT JOIN tat t ON t.hospital_id = g.hospital_id AND t.month = g.month
LEFT JOIN clm cl ON cl.hospital_id = g.hospital_id AND cl.month = g.month
LEFT JOIN fb fb ON fb.hospital_id = g.hospital_id AND fb.month = g.month
LEFT JOIN inc i ON i.hospital_id = g.hospital_id AND i.month = g.month
LEFT JOIN wrk w ON w.hospital_id = g.hospital_id AND w.month = g.month
LEFT JOIN inv iv ON iv.hospital_id = g.hospital_id AND iv.month = g.month
ORDER BY g.hospital_id, g.month;
