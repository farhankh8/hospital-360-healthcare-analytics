-- gold_network_daily : one row per calendar day in the 24-month window.
-- Counts are coalesced to 0 so daily charts are continuous.
WITH dates AS (
    SELECT CAST(d AS DATE) AS date
    FROM generate_series(DATE '2025-01-01', DATE '2026-12-31', INTERVAL 1 DAY) t(d)
),
enc AS (
    SELECT CAST(arrival_datetime AS DATE) AS date, COUNT(*) AS encounters
    FROM silver_encounters
    WHERE arrival_datetime IS NOT NULL
    GROUP BY 1
),
adm AS (
    SELECT CAST(admission_datetime AS DATE) AS date, COUNT(*) AS admissions
    FROM silver_admissions
    WHERE admission_datetime IS NOT NULL
    GROUP BY 1
),
apt AS (
    SELECT appointment_date AS date,
           COUNT(*) AS appointments,
           COUNT(*) FILTER (WHERE LOWER(status) = 'completed') AS completed_appointments,
           COUNT(*) FILTER (WHERE LOWER(status) IN ('no-show', 'no show', 'noshow')) AS no_show_appointments,
           AVG(waiting_minutes) AS avg_wait_minutes
    FROM silver_appointments
    WHERE appointment_date IS NOT NULL
    GROUP BY 1
),
rev AS (
    SELECT invoice_date AS date, SUM(net_amount) AS revenue
    FROM silver_invoices
    WHERE invoice_date IS NOT NULL
    GROUP BY 1
),
coll AS (
    SELECT payment_date AS date,
           SUM(CASE WHEN LOWER(COALESCE(payment_type, '')) = 'refund'
                    THEN -ABS(COALESCE(amount, 0))
                    ELSE COALESCE(amount, 0) END) AS collections
    FROM silver_payments
    WHERE payment_date IS NOT NULL AND LOWER(COALESCE(status, '')) = 'cleared'
    GROUP BY 1
),
beds AS (
    SELECT CAST(snapshot_datetime AS DATE) AS date,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'occupied'
                              OR COALESCE(occupied_flag, FALSE)) AS occupied_beds,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) <> 'blocked'
                              AND NOT COALESCE(blocked_flag, FALSE)) AS available_beds
    FROM silver_bed_snapshots
    WHERE snapshot_datetime IS NOT NULL
    GROUP BY 1
)
SELECT d.date,
       CAST(COALESCE(e.encounters, 0) AS INTEGER) AS encounters,
       CAST(COALESCE(a.admissions, 0) AS INTEGER) AS admissions,
       CAST(COALESCE(p.appointments, 0) AS INTEGER) AS appointments,
       CAST(COALESCE(p.completed_appointments, 0) AS INTEGER) AS completed_appointments,
       CAST(COALESCE(p.no_show_appointments, 0) AS INTEGER) AS no_show_appointments,
       COALESCE(r.revenue, 0.0) AS revenue,
       COALESCE(c.collections, 0.0) AS collections,
       CAST(COALESCE(b.occupied_beds, 0) AS INTEGER) AS occupied_beds,
       CAST(COALESCE(b.available_beds, 0) AS INTEGER) AS available_beds,
       ROUND(p.avg_wait_minutes, 2) AS avg_wait_minutes
FROM dates d
LEFT JOIN enc e ON e.date = d.date
LEFT JOIN adm a ON a.date = d.date
LEFT JOIN apt p ON p.date = d.date
LEFT JOIN rev r ON r.date = d.date
LEFT JOIN coll c ON c.date = d.date
LEFT JOIN beds b ON b.date = d.date
ORDER BY d.date;
