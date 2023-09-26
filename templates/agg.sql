SELECT 
    COUNT(*) num_delayed,
    AVG({{a_delay}}) avg_delay
FROM {{tbl_name}}
WHERE DATE({{a_sched}}) = '{{str_date}}';