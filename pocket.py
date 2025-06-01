import requests
import polars as pl
import time
from tenacity import retry, stop_after_attempt, wait_exponential

ACCESS_TOKEN= 'e525c2b1-87a3-588a-c834-1d2a3b'
CONSUMER_KEY = '11552-470488bc7a267c1c98f7695f'
BATCH_SIZE = 100

start_page = 0

@retry(stop=stop_after_attempt(5), wait=wait_exponential())
def more():
    offset = start_page * BATCH_SIZE
    resp = requests.post(
        url='https://getpocket.com/v3/get',
        json={
            'consumer_key': CONSUMER_KEY,
            'access_token': ACCESS_TOKEN,
            'state': 'all',
            'detailType': 'simple',
            'sort': 'oldest',
            'count': BATCH_SIZE,
            'offset': offset
        },
        headers={'X-Accept': 'application/json'}
    )
    resp.raise_for_status()
    batch = list(resp.json().get('list', {}).values())
    print(f"Fetched {len(batch)} items @ {offset=}")
    return pl.DataFrame(batch).select([
        pl.col("item_id").alias("id"),
        pl.coalesce([pl.col("resolved_url"), pl.col("given_url")]).alias("url"),
        pl.from_epoch("time_added", time_unit="s").dt.date().alias("date_added"),
        pl.from_epoch(pl.col("time_read").replace(0, None), time_unit="s").dt.date().alias("date_read"),
    ])

while True:
    items = more()
    items.write_csv(f"pocket-{start_page}.csv")
    if len(items) < BATCH_SIZE:
        break
    start_page += 1
    time.sleep(0.5)  # be polite
