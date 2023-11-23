SELECT
    ROW_NUMBER() OVER (ORDER BY CAST({{a_delay}} AS INTEGER) DESC) delay_rank,
    {{flight_num}},
    REPLACE(
    REPLACE(
    REPLACE({{a_port}}, ' International Airport', ''),
    ' International', ''),
    ' Airport', '') AS {{a_port}},
    REPLACE(
    REPLACE(
    REPLACE({{d_port}}, ' International Airport', ''),
    ' International', ''),
    ' Airport', '') AS {{d_port}},
    {{a_delay}}
FROM {{tbl_name}}
WHERE DATE({{a_sched}}) = '{{str_date}}'
AND {{a_delay}} IS NOT NULL
ORDER BY delay_rank
LIMIT {{num_delay}};
