import asyncio
import logging
import csv
from httpx import AsyncClient, RequestError, TimeoutException
from aiolimiter import AsyncLimiter
import aiofiles 

MAX_RPS = 18      
MAX_CONCURRENT = 50  
OUTPUT_FILE = "orders_async.csv"
FIELDS = ["order_id","account_id","company","status","currency","subtotal","tax","total","created_at"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

async def fetch_item(client, item_id, limiter, semaphore, max_retries=3):
    url = f"http://127.0.0.1:8000/item/{item_id}"
    retries = 0

    async with semaphore: 
        while retries < max_retries:
            try:
                async with limiter: 
                    resp = await client.get(url, timeout=5.0)
                    
                if resp.status_code == 429: 
                    retry_after = int(resp.headers.get("Retry-After", 1))
                    logging.warning(f"{item_id} 429, retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue
                elif 500 <= resp.status_code < 600:  
                    logging.warning(f"{item_id} {resp.status_code}, retrying in 1s")
                    await asyncio.sleep(1)
                    retries += 1
                    continue
                elif 400 <= resp.status_code < 500:
                    logging.error(f"{item_id} {resp.status_code}, non-retryable")
                    return None
                
                return resp.json()  
            
            except (RequestError, TimeoutException) as e:
                logging.warning(f"{item_id} exception {e}, retrying...")
                retries += 1
                await asyncio.sleep(1)
        
        logging.error(f"{item_id} failed after {max_retries} retries")
        return None

async def run_reqs(num_items=1000):
    limiter = AsyncLimiter(MAX_RPS, 1) 
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results = []

    async with AsyncClient() as client:
        tasks = [fetch_item(client, i, limiter, semaphore) for i in range(1, num_items+1)]
        
        for future in asyncio.as_completed(tasks):
            data = await future
            if data:
                row = {field: data.get(field) for field in FIELDS}
                results.append(row)
    
    return results

async def write_csv(rows, filename=OUTPUT_FILE):
    async with aiofiles.open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        await f.write(','.join(FIELDS) + '\n')  
        
        for row in rows:
            line = ','.join(str(row.get(f, "")) for f in FIELDS) + '\n'
            await f.write(line)

async def main():
    orders = await run_reqs(1000)
    await write_csv(orders)
    logging.info(f"Saved {len(orders)} orders to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
