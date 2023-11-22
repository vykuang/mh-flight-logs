WITH RECURSIVE
    filtered(airline, flight, delay) AS (
        SELECT
            substr(flight_iata_number, 1, 2) airline,
            flight_iata_number flight,
            arr_delay delay
        FROM {{tbl_name}}
        WHERE airline = '{{airline_iata}}'
        AND flight_date = '{{str_date}}'
    )
SELECT 
    count(flight) total,
    count(delay) num_delayed,
    avg(delay) avg_delayed
FROM filtered
    