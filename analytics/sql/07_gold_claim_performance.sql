-- gold_claim_performance : payer x hospital x month claim adjudication.
-- denial_rate uses adjudicated claims only (Approved + Denied).
WITH grid AS (
    SELECT h.hospital_id, p.payer_id, p.payer_name, m.month
    FROM dim_hospital h CROSS JOIN dim_payer p CROSS JOIN dim_month m
    WHERE h.hospital_id IN ('H01','H02','H03','H04','H05','H06','H07','H08','H09','H10')
),
clm AS (
    SELECT hospital_id, payer_id, DATE_TRUNC('month', claim_date)::DATE AS month,
           COUNT(*) AS claims,
           COUNT(*) FILTER (WHERE LOWER(status) = 'approved') AS approved,
           COUNT(*) FILTER (WHERE LOWER(status) = 'denied') AS denied,
           SUM(claim_amount) AS claimed_amount,
           SUM(approved_amount) AS approved_amount,
           SUM(paid_amount) AS paid_amount,
           AVG(processing_days) AS avg_processing_days
    FROM silver_claims
    WHERE claim_date IS NOT NULL
    GROUP BY 1, 2, 3
),
appealed_claims AS (
    SELECT DISTINCT claim_id FROM silver_claim_events
    WHERE LOWER(event_type) = 'appealed'
),
appeals AS (
    SELECT c.hospital_id, c.payer_id, DATE_TRUNC('month', c.claim_date)::DATE AS month,
           COUNT(DISTINCT e.claim_id) FILTER (WHERE LOWER(e.event_type) = 'appealed') AS appeals,
           COUNT(DISTINCT e.claim_id) FILTER (
               WHERE LOWER(e.event_type) = 'approved'
                 AND e.claim_id IN (SELECT claim_id FROM appealed_claims)
           ) AS appeals_approved
    FROM silver_claim_events e
    JOIN silver_claims c ON e.claim_id = c.claim_id
    WHERE c.claim_date IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT g.hospital_id, g.payer_id, g.payer_name, g.month,
       CAST(COALESCE(c.claims, 0) AS INTEGER) AS claims,
       CAST(COALESCE(c.approved, 0) AS INTEGER) AS approved,
       CAST(COALESCE(c.denied, 0) AS INTEGER) AS denied,
       ROUND(100.0 * c.denied / NULLIF(c.approved + c.denied, 0), 2) AS denial_rate,
       COALESCE(c.claimed_amount, 0.0) AS claimed_amount,
       COALESCE(c.approved_amount, 0.0) AS approved_amount,
       COALESCE(c.paid_amount, 0.0) AS paid_amount,
       ROUND(c.avg_processing_days, 2) AS avg_processing_days,
       CAST(COALESCE(a.appeals, 0) AS INTEGER) AS appeals,
       ROUND(100.0 * a.appeals_approved / NULLIF(a.appeals, 0), 2) AS appeal_success_rate
FROM grid g
LEFT JOIN clm c ON c.hospital_id = g.hospital_id AND c.payer_id = g.payer_id AND c.month = g.month
LEFT JOIN appeals a ON a.hospital_id = g.hospital_id AND a.payer_id = g.payer_id AND a.month = g.month
ORDER BY g.hospital_id, g.payer_id, g.month;
