CREATE TABLE {{tbl_name}}(
    {{json_col}} JSON,
    flight_iata_number TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.flight.iata')) VIRTUAL,
    dep_airport_code TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.departure.iata')) VIRTUAL,
    arr_airport_code TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.arrival.iata')) VIRTUAL,
    arr_time TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.arrival.scheduled')) VIRTUAL,
    arr_delay TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.arrival.delay')) VIRTUAL);
CREATE UNIQUE INDEX flight_index 
ON {{tbl_name}}(flight_iata_number, dep_airport_code, arr_airport_code, arr_time);
