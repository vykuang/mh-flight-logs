CREATE TABLE {{tbl_name}}(
    {{json_col}} JSON,
    flight_num TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.flight.iata')) VIRTUAL,
    start TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.departure.iata')) VIRTUAL,
    dest TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.arrival.iata')) VIRTUAL,
    ts_takeoff TEXT GENERATED ALWAYS AS (JSON_EXTRACT({{json_col}}, '$.arrival.iata')) VIRTUAL
);