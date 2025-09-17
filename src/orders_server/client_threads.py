import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from ratelimit import limits, sleep_and_retry

MAX_RPS = 18  
MAX_WORKERS = 8 
OUTPUT_FILE = "orders.csv"
FIELDS = ["order_id","account_id","company","status","currency","subtotal","tax","total","created_at"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def fetch_item(item_id, max_retries=3):
    url = f"http://127.0.0.1:8000/item/{item_id}"
    retries = 0

    while retries < max_retries:
        try:
            resp = httpx.get(url, timeout=5)
            
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 1))
                logging.warning(f"{item_id} 429, retrying after {retry_after}s")
                time.sleep(retry_after)
                retries += 1
                continue
            elif 500 <= resp.status_code < 600:  
                logging.warning(f"{item_id} {resp.status_code}, retrying in 1s")
                time.sleep(1)
                retries += 1
                continue
            elif 400 <= resp.status_code < 500:
                logging.error(f"{item_id} {resp.status_code}, non-retryable")
                return item_id, resp.status_code, None
            
            return item_id, resp.status_code, resp.json()
        
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logging.warning(f"{item_id} exception {e}, retrying...")
            retries += 1
            time.sleep(1)

    logging.error(f"{item_id} failed after {max_retries} retries")
    return item_id, None, None
    
def run_reqs(num_reqs=50):
    results = []
    item_ids = list(range(1, num_reqs + 1))

    with ThreadPoolExecutor(MAX_WORKERS) as executor:
        for i in range(0, len(item_ids), MAX_RPS):
            batch = item_ids[i:i + MAX_RPS]
            futures = [executor.submit(fetch_item, item_id) for item_id in batch]

            for future in as_completed(futures):
                item_id, status, data = future.result()

                if status == 200:
                    row = {field: data.get(field) for field in FIELDS} 
                    results.append(row)
                else:
                    logging.warning(f"Failed to fetch {item_id}: {status}, {data}")

            time.sleep(1)

    return results


if __name__ == "__main__":
    orders = run_reqs()
    
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(orders)
    
    logging.info(f"Saved {len(orders)} orders to {OUTPUT_FILE}")

