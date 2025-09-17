# Orders Client

This project provides two Python clients to fetch order data from a REST API and save it to a CSV file:

1. **Synchronous / Threaded Client** (`client_threads.py`)
2. **Asynchronous Client** (`client_async.py`)

Both clients handle rate limiting, retries on errors, and CSV output in a structured format.

---

## Features

- Fetch order data from `http://127.0.0.1:8000/item/{item_id}`
- Handle retries:
  - `429 Too Many Requests` → wait `Retry-After` seconds
  - `5xx` → retry after 1 second
  - Network timeouts / transport errors → retry (bounded attempts)
- Logs retries and failures
- Writes CSV output with the following fields:

Usage
Threaded Client
python src/orders_server/client_threads.py


Configurable parameters:

MAX_WORKERS → number of threads

MAX_RPS → requests per second

Async Client
python src/orders_server/client_async.py

Uses asyncio.Semaphore to limit concurrency (burst requests)

Uses aiolimiter.AsyncLimiter for rate limiting (e.g., 18 req/sec)

Writes CSV output asynchronously (optional with aiofiles)

OUTPUT_FILE → CSV output file

Produces orders.csv after fetching orders.
