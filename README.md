# Malaysia Airline Flight Delays

This project analyzes all recent malaysia airline flights and puts out a tweet summarizing how many flights were delayed, and for how long.

1. call aviationstack API for late flights
2. store as json
3. parse into sqlite db
4. query db to populate tweet
5. call twitter API to post tweet

## APIs

### aviationstack

Free tier provides 1000 calls/month, with some limitations:

- only 100 results
- no date filtering [premium plan only]

For instances with > 100 results, repeat API calls while rolling the offsets to retrieve the entire set

### twitter

Uses v2 API via OAuth1.0. Requires

- consumer key
- consumer secret
- access token
- access secret

Obtained from twitter developer account portal

## Usage

1. git clone
1. add `.env` to project root with the following info:

    ```bash
    AVIATION_API_KEY=
    TWITTER_API_KEY=
    TWITTER_API_SECRET=
    TWITTER_ACCESS_TOKEN=
    TWITTER_ACCESS_SECRET=
    ```

1. `docker build -t asean-flight-logs .`
1. `docker run --env-file .env asean-flight-logs`

## todo

1. volume for json responses and sqlite db
    - container unable to open sqlite db after putting PC to sleep?
    - exec was able to reach the db
    - not the same db as host; cannot find `import_flight_records` table, or any table
       - mount `./data` to something besides `/app`, i.e. `/data` (not inside `/app`)
    - bind mounting `main.py` and calling it with `./main.py` caused "no such file" error
       - works when I exec into the container. `main.py` is in `/app`, and I can run it
       - add `WORKDIR` to runtime image in Dockerfile; defaults to root `/` otherwise
1. logging - ok
    - tweet is posted, but no output. logging is not captured by STDOUT normally
    - add `sys.stdout` to `StreamHandler`
    - add `FileHandler('debug.log')`
1. retries on API call timeouts - ok
    - use requests.Session()
    - pass Session object to `get_flight_api` for reuse
    - rewrite `get_flight_api`, or fold into `get_all_delays`
1. expand to other Asean flag carrier airlines, as well as other popular regionals for comparisons
    - SEA:
        - Royal Brunei Airlines
        - Cambodia Angkor Air
        - Garuda Indonesia
        - Lao Airlines
        - Myanmar National Airlines
        - Philippine Airlines
        - Singapore Airlines
        - Thai Airways International
        - Vietnam Airlines
    - Others:
        - China Airlines (TW)
        - Air China
        - Cathay Pacific
        - Air Asia