-- gold_inventory : inventory category x hospital x month.
-- Running stock is the cumulative sum of signed movements per item; low_stock
-- is stock <= reorder_level, stockouts is stock <= 0.
WITH categories AS (
    SELECT DISTINCT category FROM dim_inventory_item WHERE category IS NOT NULL
),
grid AS (
    SELECT h.hospital_id, c.category, m.month
    FROM dim_hospital h CROSS JOIN categories c CROSS JOIN dim_month m
    WHERE h.hospital_id IN ('H01','H02','H03','H04','H05','H06','H07','H08','H09','H10')
),
monthly AS (
    SELECT hospital_id, item_id, DATE_TRUNC('month', movement_date)::DATE AS month,
           SUM(quantity) AS net_qty,
           SUM(CASE WHEN LOWER(movement_type) = 'receipt' THEN quantity * COALESCE(unit_cost, 0) ELSE 0 END) AS receipt_value,
           SUM(CASE WHEN LOWER(movement_type) IN ('issue', 'waste') THEN ABS(quantity) * COALESCE(unit_cost, 0) ELSE 0 END) AS issue_value,
           SUM(CASE WHEN LOWER(movement_type) = 'expiry' THEN ABS(quantity) * COALESCE(unit_cost, 0) ELSE 0 END) AS expired_value,
           SUM(CASE WHEN LOWER(movement_type) = 'waste' THEN ABS(quantity) * COALESCE(unit_cost, 0) ELSE 0 END) AS waste,
           COUNT(*) FILTER (WHERE LOWER(movement_type) = 'issue') AS issue_events
    FROM silver_inventory_movements
    WHERE movement_date IS NOT NULL
    GROUP BY 1, 2, 3
),
stock AS (
    SELECT m.*, i.category, i.unit_cost, i.reorder_level,
           SUM(m.net_qty) OVER (PARTITION BY m.hospital_id, m.item_id
                                ORDER BY m.month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_qty
    FROM monthly m
    LEFT JOIN dim_inventory_item i ON m.item_id = i.item_id
),
agg AS (
    SELECT hospital_id, category, month,
           SUM(GREATEST(cum_qty, 0) * COALESCE(unit_cost, 0)) AS inventory_value,
           COUNT(DISTINCT item_id) FILTER (WHERE cum_qty <= 0) AS stockouts,
           COUNT(DISTINCT item_id) FILTER (WHERE cum_qty > 0 AND cum_qty <= COALESCE(reorder_level, 0)) AS low_stock,
           SUM(expired_value) AS expired_value,
           SUM(waste) AS waste,
           SUM(issue_value) AS issue_value
    FROM stock
    WHERE category IS NOT NULL
    GROUP BY 1, 2, 3
),
po AS (
    SELECT hospital_id, DATE_TRUNC('month', order_date)::DATE AS month,
           COUNT(*) AS purchase_orders,
           SUM(total_amount) AS procurement_value,
           COUNT(*) FILTER (WHERE received_date IS NOT NULL AND received_date <= expected_date) AS on_time,
           COUNT(*) FILTER (WHERE received_date IS NOT NULL) AS received
    FROM silver_purchase_orders
    WHERE order_date IS NOT NULL
    GROUP BY 1, 2
)
SELECT g.hospital_id, g.category, g.month,
       COALESCE(a.inventory_value, 0.0) AS inventory_value,
       CAST(COALESCE(a.stockouts, 0) AS INTEGER) AS stockouts,
       CAST(COALESCE(a.low_stock, 0) AS INTEGER) AS low_stock,
       COALESCE(a.expired_value, 0.0) AS expired_value,
       COALESCE(a.waste, 0.0) AS waste,
       CASE WHEN COALESCE(a.inventory_value, 0) = 0 THEN NULL
            ELSE ROUND(a.issue_value / a.inventory_value, 2) END AS turnover,
       CAST(COALESCE(p.purchase_orders, 0) AS INTEGER) AS purchase_orders,
       COALESCE(p.procurement_value, 0.0) AS procurement_value,
       ROUND(100.0 * p.on_time / NULLIF(p.received, 0), 2) AS supplier_on_time_rate
FROM grid g
LEFT JOIN agg a ON a.hospital_id = g.hospital_id AND a.category = g.category AND a.month = g.month
LEFT JOIN po p ON p.hospital_id = g.hospital_id AND p.month = g.month
ORDER BY g.hospital_id, g.category, g.month;
