import requests
import polars as pl
import time

CONSUMER_KEY = '11552-470488bc7a267c1c98f7695f'


def fetch(access_token: str, offset: int = 0):
    time.sleep(0.5)  # be polite
    count = 100
    resp = requests.post(
        url='https://getpocket.com/v3/get',
        json={
            'consumer_key': CONSUMER_KEY,
            'access_token': access_token,
            'state': 'all',
            'detailType': 'simple',
            'count': count,
            'offset': offset
        },
        headers={'X-Accept': 'application/json'}
    )
    resp.raise_for_status()
    batch = list(resp.json().get('list', {}).values())
    print(f"Fetched {len(batch)} items @ {offset=}")
    more = [] if len(batch) < count else fetch(access_token=access_token, offset=offset + count)
    return batch + more


def fetch_df(access_token: str):
    return pl.DataFrame(fetch(access_token)).select([
        pl.col("item_id").alias("id"),
        pl.coalesce([pl.col("resolved_url"), pl.col("given_url")]).alias("url"),
        pl.from_epoch("time_added", time_unit="s").dt.date(),
        pl.from_epoch(pl.col("time_read").replace(0, None), time_unit="s").dt.date(),
    ])


df = fetch_df(access_token='e525c2b1-87a3-588a-c834-1d2a3b')
df.write_csv("pocket.csv")

