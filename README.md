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

1. `sh run.sh` - convenience script to run `docker compose up` and then `docker compose down` to remove finished containers

## todo

1. volume for json responses and sqlite db
    - container unable to open sqlite db after putting PC to sleep?
    - exec was able to reach the db
    - not the same db as host; cannot find `import_flight_records` table, or any table
       - mount `./data` to something besides `/app`, i.e. `/data` (not inside `/app`)
    - bind mounting `main.py` and calling it with `./main.py` caused "no such file" error
       - works when I exec into the container. `main.py` is in `/app`, and I can run it
       - fix by add `WORKDIR` to runtime image in Dockerfile; defaults to root `/` otherwise
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
    - will need additional API keys for each airline to have enough quota
        - each airline requires 10-20 calls per day
        - 1000 calls / 30 days / 20 calls per airline ~= 1.5 airlines
1. Change entrypoint from `./main.py` to `python main.py` to avoid permission error on rpi
1. look for local files before fetching all offsets? this is beginning to stretch into the realm of an orchestrator
1. improve logging - at least log what date we're looking for
1. test if multiple retry is working
   - check

