-- gold_bed_utilization : ward x month bed capacity and utilisation.
-- Snapshot counts are used as bed-day equivalents (one snapshot per bed per day
-- in the generator). Blocked beds are excluded from the occupancy denominator.
WITH beds AS (
    SELECT hospital_id, ward, DATE_TRUNC('month', snapshot_datetime)::DATE AS month,
           COUNT(DISTINCT bed_id) AS total_beds,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'occupied'
                              OR COALESCE(occupied_flag, FALSE)) AS occupied_bed_days,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'available'
                              AND NOT COALESCE(occupied_flag, FALSE)
                              AND NOT COALESCE(blocked_flag, FALSE)) AS available_bed_days,
           COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'blocked'
                              OR COALESCE(blocked_flag, FALSE)) AS blocked_bed_days
    FROM silver_bed_snapshots
    WHERE snapshot_datetime IS NOT NULL
    GROUP BY 1, 2, 3
),
adm AS (
    SELECT hospital_id, ward,
           DATE_TRUNC('month', admission_datetime)::DATE AS adm_month,
           DATE_TRUNC('month', discharge_datetime)::DATE AS dis_month,
           los_days, boarding_hours, discharge_datetime, readmission_flag
    FROM silver_admissions
    WHERE admission_datetime IS NOT NULL
),
los AS (
    SELECT hospital_id, ward, dis_month AS month,
           AVG(los_days) AS avg_los_days,
           COUNT(*) AS discharges
    FROM adm WHERE discharge_datetime IS NOT NULL
    GROUP BY 1, 2, 3
),
boarding AS (
    SELECT hospital_id, ward, adm_month AS month, AVG(boarding_hours) AS avg_boarding_hours
    FROM adm
    GROUP BY 1, 2, 3
)
SELECT b.hospital_id, b.ward, b.month,
       CAST(b.total_beds AS INTEGER) AS total_beds,
       b.occupied_bed_days AS occupied_bed_days,
       (b.occupied_bed_days + b.available_bed_days) AS available_bed_days,
       b.blocked_bed_days AS blocked_bed_days,
       ROUND(100.0 * b.occupied_bed_days
             / NULLIF(b.occupied_bed_days + b.available_bed_days, 0), 2) AS occupancy_rate,
       ROUND(l.avg_los_days, 2) AS avg_los_days,
       ROUND(l.discharges / NULLIF(b.total_beds, 0), 2) AS bed_turnover,
       ROUND(bo.avg_boarding_hours, 2) AS avg_boarding_hours
FROM beds b
LEFT JOIN los l ON l.hospital_id = b.hospital_id AND l.ward = b.ward AND l.month = b.month
LEFT JOIN boarding bo ON bo.hospital_id = b.hospital_id AND bo.ward = b.ward AND bo.month = b.month
ORDER BY b.hospital_id, b.ward, b.month;
