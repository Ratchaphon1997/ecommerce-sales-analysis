-- ============================================================
-- queries.sql
-- E-Commerce Sales Analysis — SQL Query Collection
-- Compatible with: SQLite / DuckDB / PostgreSQL / BigQuery*
-- (* minor syntax adjustments may be needed for BigQuery)
-- ============================================================


-- ─── 1. OVERVIEW KPIs ───────────────────────────────────────────────────────
-- Top-line metrics for the entire period

SELECT
    COUNT(DISTINCT order_id)                        AS total_orders,
    COUNT(DISTINCT customer_id)                     AS unique_customers,
    ROUND(SUM(total_amount), 2)                     AS total_revenue,
    ROUND(AVG(total_amount), 2)                     AS avg_order_value,
    ROUND(100.0 * SUM(CASE WHEN status = 'Returned'  THEN 1 ELSE 0 END)
              / COUNT(*), 2)                        AS return_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END)
              / COUNT(*), 2)                        AS cancellation_rate_pct
FROM orders
WHERE status IN ('Completed', 'Returned', 'Cancelled');


-- ─── 2. MONTHLY REVENUE TREND ───────────────────────────────────────────────
-- Revenue trend with Month-over-Month growth rate

WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', order_date)   AS year_month,
        ROUND(SUM(total_amount), 2)     AS revenue
    FROM orders
    WHERE status = 'Completed'
    GROUP BY year_month
),
with_lag AS (
    SELECT
        year_month,
        revenue,
        LAG(revenue) OVER (ORDER BY year_month) AS prev_revenue
    FROM monthly
)
SELECT
    year_month,
    revenue,
    prev_revenue,
    ROUND(100.0 * (revenue - prev_revenue) / NULLIF(prev_revenue, 0), 2) AS mom_growth_pct
FROM with_lag
ORDER BY year_month;


-- ─── 3. REVENUE BY CATEGORY ─────────────────────────────────────────────────
-- Which product category drives the most revenue?

SELECT
    p.category,
    COUNT(DISTINCT oi.order_id)         AS orders_count,
    SUM(oi.quantity)                    AS units_sold,
    ROUND(SUM(oi.subtotal), 2)          AS revenue,
    ROUND(AVG(oi.unit_price), 2)        AS avg_unit_price,
    ROUND(100.0 * SUM(oi.subtotal)
        / SUM(SUM(oi.subtotal)) OVER(), 2) AS revenue_share_pct
FROM order_items oi
JOIN products    p  ON oi.product_id = p.product_id
JOIN orders      o  ON oi.order_id   = o.order_id
WHERE o.status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;


-- ─── 4. TOP 10 PRODUCTS BY REVENUE ──────────────────────────────────────────

SELECT
    p.product_id,
    p.product_name,
    p.category,
    COUNT(DISTINCT oi.order_id)     AS orders,
    SUM(oi.quantity)                AS units_sold,
    ROUND(SUM(oi.subtotal), 2)      AS revenue,
    ROUND(AVG(p.rating), 1)         AS avg_rating
FROM order_items oi
JOIN products    p ON oi.product_id = p.product_id
JOIN orders      o ON oi.order_id   = o.order_id
WHERE o.status = 'Completed'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;


-- ─── 5. CUSTOMER ACQUISITION COHORT ANALYSIS ────────────────────────────────
-- Retention by monthly cohort (how many customers return each month)

WITH customer_cohort AS (
    SELECT
        c.customer_id,
        STRFTIME('%Y-%m', c.signup_date)    AS cohort_month,
        STRFTIME('%Y-%m', o.order_date)     AS order_month
    FROM customers c
    JOIN orders    o ON c.customer_id = o.customer_id
    WHERE o.status = 'Completed'
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM customer_cohort
    GROUP BY cohort_month
),
cohort_data AS (
    SELECT
        cohort_month,
        order_month,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM customer_cohort
    GROUP BY cohort_month, order_month
)
SELECT
    cd.cohort_month,
    cd.order_month,
    cs.cohort_customers,
    cd.active_customers,
    ROUND(100.0 * cd.active_customers / cs.cohort_customers, 2) AS retention_pct
FROM cohort_data  cd
JOIN cohort_size  cs ON cd.cohort_month = cs.cohort_month
ORDER BY cd.cohort_month, cd.order_month;


-- ─── 6. RFM SEGMENTATION ────────────────────────────────────────────────────
-- Recency / Frequency / Monetary scoring using NTILE

WITH base AS (
    SELECT
        customer_id,
        MAX(order_date)                      AS last_order_date,
        COUNT(order_id)                      AS frequency,
        ROUND(SUM(total_amount), 2)          AS monetary
    FROM orders
    WHERE status = 'Completed'
    GROUP BY customer_id
),
rfm_raw AS (
    SELECT
        customer_id,
        JULIANDAY('2025-01-01') - JULIANDAY(last_order_date) AS recency_days,
        frequency,
        monetary
    FROM base
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- Lower recency = better → reverse NTILE
        5 - NTILE(4) OVER (ORDER BY recency_days)  + 1 AS r_score,
        NTILE(4) OVER (ORDER BY frequency)              AS f_score,
        NTILE(4) OVER (ORDER BY monetary)               AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score AS rfm_total,
    CASE
        WHEN r_score + f_score + m_score >= 10 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3     THEN 'Loyal Customers'
        WHEN r_score >= 3                      THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND f_score >= 3     THEN 'At Risk'
        WHEN r_score + f_score + m_score <= 5  THEN 'Lost / Churned'
        ELSE                                        'Need Attention'
    END AS segment
FROM rfm_scored
ORDER BY rfm_total DESC;


-- ─── 7. CHANNEL PERFORMANCE ─────────────────────────────────────────────────
-- Revenue and AOV by sales channel

SELECT
    channel,
    COUNT(*)                            AS total_orders,
    COUNT(DISTINCT customer_id)         AS unique_customers,
    ROUND(SUM(total_amount), 2)         AS revenue,
    ROUND(AVG(total_amount), 2)         AS avg_order_value,
    ROUND(100.0 * SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END)
              / COUNT(*), 2)            AS return_rate_pct
FROM orders
GROUP BY channel
ORDER BY revenue DESC;


-- ─── 8. REGIONAL PERFORMANCE ────────────────────────────────────────────────

SELECT
    region,
    COUNT(DISTINCT customer_id)         AS customers,
    COUNT(*)                            AS orders,
    ROUND(SUM(total_amount), 2)         AS revenue,
    ROUND(AVG(total_amount), 2)         AS avg_order_value
FROM orders
WHERE status = 'Completed'
GROUP BY region
ORDER BY revenue DESC;


-- ─── 9. BASKET SIZE DISTRIBUTION ────────────────────────────────────────────
-- Average items per order and basket-size buckets

WITH basket AS (
    SELECT
        order_id,
        SUM(quantity) AS items_in_order
    FROM order_items
    GROUP BY order_id
)
SELECT
    CASE
        WHEN items_in_order = 1 THEN '1 item'
        WHEN items_in_order BETWEEN 2 AND 3 THEN '2-3 items'
        WHEN items_in_order BETWEEN 4 AND 6 THEN '4-6 items'
        ELSE '7+ items'
    END AS basket_size,
    COUNT(*) AS order_count,
    ROUND(AVG(o.total_amount), 2) AS avg_revenue
FROM basket b
JOIN orders o ON b.order_id = o.order_id
WHERE o.status = 'Completed'
GROUP BY basket_size
ORDER BY MIN(items_in_order);


-- ─── 10. PAYMENT METHOD MIX ─────────────────────────────────────────────────

SELECT
    payment,
    COUNT(*)                            AS orders,
    ROUND(SUM(total_amount), 2)         AS revenue,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS order_share_pct
FROM orders
WHERE status = 'Completed'
GROUP BY payment
ORDER BY orders DESC;
