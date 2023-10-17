WITH RECURSIVE 
delays(flight_date, start, dest, delay) as (
    SELECT
        json_extract({colname_json},'$.flight_date') as date,
        json_extract({colname_json},'$.departure.airport') as start,
        json_extract({colname_json},'$.arrival.airport') as dest,
        CAST(json_extract({colname_json},'$.arrival.delay') AS INTEGER) as delay
    FROM {tblname_json}
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