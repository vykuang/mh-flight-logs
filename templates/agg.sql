WITH RECURSIVE 
    t(flight_date, total) AS (
        SELECT 
            DATE(DATETIME(arr_time)) flight_date,
            COUNT(*) total 
        FROM {{tbl_name}}
        WHERE flight_date = '{{str_date}}')
SELECT 
    t.total total,
    COUNT(arr_delay) num_delayed,
    AVG(CAST(arr_delay AS INTEGER)) avg_delay
FROM {{tbl_name}} d LEFT JOIN t
WHERE DATE(d.arr_time) = t.flight_date
AND arr_delay > 0;