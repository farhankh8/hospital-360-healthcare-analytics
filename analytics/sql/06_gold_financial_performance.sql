-- gold_financial_performance : finance by hospital-department-month.
-- collections = cleared payments net of refunds; writeoffs are proxied by the
-- balance of overdue invoices (documented in the KPI glossary).
WITH depts AS (
    SELECT hospital_id, department_id FROM dim_department
),
grid AS (
    SELECT d.hospital_id, d.department_id, m.month FROM depts d CROSS JOIN dim_month m
),
rev AS (
    SELECT e.hospital_id, e.department_id, DATE_TRUNC('month', i.invoice_date)::DATE AS month,
           SUM(i.gross_amount) AS gross_revenue,
           SUM(i.net_amount) AS net_revenue,
           SUM(i.balance_amount) AS outstanding_balance,
           AVG(i.net_amount) AS avg_invoice_value,
           SUM(CASE WHEN LOWER(COALESCE(i.invoice_status, '')) = 'overdue'
                    THEN COALESCE(i.balance_amount, 0) ELSE 0 END) AS writeoffs,
           COUNT(*) AS invoice_count
    FROM silver_invoices i
    JOIN silver_encounters e ON i.encounter_id = e.encounter_id
    WHERE i.invoice_date IS NOT NULL
    GROUP BY 1, 2, 3
),
cash AS (
    SELECT e.hospital_id, e.department_id, DATE_TRUNC('month', p.payment_date)::DATE AS month,
           SUM(CASE WHEN LOWER(COALESCE(p.payment_type, '')) = 'refund'
                    THEN -ABS(COALESCE(p.amount, 0)) ELSE COALESCE(p.amount, 0) END) AS collections,
           SUM(CASE WHEN LOWER(COALESCE(p.payment_type, '')) = 'refund'
                    THEN ABS(COALESCE(p.amount, 0)) ELSE 0 END) AS refunds
    FROM silver_payments p
    JOIN silver_invoices i ON p.invoice_id = i.invoice_id
    JOIN silver_encounters e ON i.encounter_id = e.encounter_id
    WHERE p.payment_date IS NOT NULL AND LOWER(COALESCE(p.status, '')) = 'cleared'
    GROUP BY 1, 2, 3
),
base AS (
    SELECT g.hospital_id, g.department_id, g.month,
           COALESCE(r.gross_revenue, 0.0) AS gross_revenue,
           COALESCE(r.net_revenue, 0.0) AS net_revenue,
           COALESCE(c.collections, 0.0) AS collections,
           COALESCE(r.outstanding_balance, 0.0) AS outstanding_balance,
           r.avg_invoice_value,
           COALESCE(c.refunds, 0.0) AS refunds,
           COALESCE(r.writeoffs, 0.0) AS writeoffs
    FROM grid g
    LEFT JOIN rev r ON r.hospital_id = g.hospital_id AND r.department_id = g.department_id AND r.month = g.month
    LEFT JOIN cash c ON c.hospital_id = g.hospital_id AND c.department_id = g.department_id AND c.month = g.month
)
SELECT b.hospital_id, b.department_id, b.month,
       b.gross_revenue, b.net_revenue, b.collections, b.outstanding_balance,
       -- Cash collected in a month can settle prior-period invoices, so the
       -- rate is bounded to 0..100. CASE keeps a zero denominator as NULL.
       CASE WHEN b.net_revenue = 0 THEN NULL
            ELSE ROUND(GREATEST(0.0, LEAST(100.0,
                   100.0 * b.collections / b.net_revenue)), 2)
       END AS collection_rate,
       ROUND(b.avg_invoice_value, 2) AS avg_invoice_value,
       b.refunds, b.writeoffs,
       ROUND(100.0 * (b.net_revenue - COALESCE(LAG(b.net_revenue) OVER (
                 PARTITION BY b.hospital_id, b.department_id ORDER BY b.month), 0))
             / NULLIF(LAG(b.net_revenue) OVER (
                 PARTITION BY b.hospital_id, b.department_id ORDER BY b.month), 0), 2) AS revenue_growth_pct
FROM base b
ORDER BY b.hospital_id, b.department_id, b.month;
