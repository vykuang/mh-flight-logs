WITH RECURSIVE 
delays(flight_date, start, dest, delay) as (
    SELECT
        json_extract({{json_col}},'$.flight_date') as flight_date,
        json_extract({{json_col}},'$.departure.airport') as start,
        json_extract({{json_col}},'$.arrival.airport') as dest,
        CAST(json_extract({{json_col}},'$.arrival.delay') AS INTEGER) as delay
    FROM {{tbl_name}}
)
SELECT
    flight_date,
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