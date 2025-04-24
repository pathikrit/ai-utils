import requests
import polars as pl
import time
from tenacity import retry, stop_after_attempt, wait_exponential

CONSUMER_KEY = '11552-470488bc7a267c1c98f7695f'


def fetch(access_token: str):
    count = 100
    all = []

    @retry(stop=stop_after_attempt(5), wait=wait_exponential())
    def more():
        resp = requests.post(
            url='https://getpocket.com/v3/get',
            json={
                'consumer_key': CONSUMER_KEY,
                'access_token': access_token,
                'state': 'all',
                'detailType': 'simple',
                'sort': 'oldest',
                'count': count,
                'offset': len(all)
            },
            headers={'X-Accept': 'application/json'}
        )
        resp.raise_for_status()
        batch = list(resp.json().get('list', {}).values())
        print(f"Fetched {len(batch)} items @ offset={len(all)}")
        return batch

    while True:
        items = more()
        all.extend(items)
        if len(items) < count:
            break
        time.sleep(0.5)  # be polite

    return pl.DataFrame(all).select([
        pl.col("item_id").alias("id"),
        pl.coalesce([pl.col("resolved_url"), pl.col("given_url")]).alias("url"),
        pl.from_epoch("time_added", time_unit="s").dt.date().alias("date_added"),
        pl.from_epoch(pl.col("time_read").replace(0, None), time_unit="s").dt.date().alias("date_read"),
    ])


df = fetch(access_token='e525c2b1-87a3-588a-c834-1d2a3b')
df.write_csv("pocket.csv")
