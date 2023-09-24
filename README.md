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
1. logging
1. retries on API call timeouts
1. expand to other airlines for comparisons