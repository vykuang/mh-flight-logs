WITH RECURSIVE 
delays(flight_num, start, dest, delay) as (
    SELECT
        flight_iata_number as flight_num,
        json_extract({{json_col}},'$.departure.airport') as start,
        json_extract({{json_col}},'$.arrival.airport') as dest,
        CAST(arr_delay AS INTEGER) as delay
    FROM {{tbl_name}}
    WHERE flight_date = '{{str_date}}'
)
SELECT
    flight_num,
    REPLACE(
    REPLACE(
    REPLACE(start, ' International Airport', ''), 
    ' International', ''),
    ' Airport', '') AS start,
    REPLACE(
    REPLACE(
    REPLACE(dest, ' International Airport', ''), 
    ' International', ''),
    ' Airport', '') AS dest,
    delay
FROM delays
ORDER BY delay DESC
LIMIT 3;
