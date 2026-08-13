# Rate Limiter Lab

Rate Limiter Lab is an engineering-focused educational project designed to explore, implement, test, and compare various rate-limiting algorithms, scaling from basic in-memory single-node rate limiters to highly concurrent and distributed systems powered by Redis and Docker Compose.

---

## Problem
In modern web architectures, API rate limiting is a critical defense mechanism used to control the rate of traffic sent by clients. Without effective rate limiting, systems are vulnerable to:
- **Denial of Service (DoS / DDoS) attacks**: Malicious clients overwhelming the system.
- **Resource Starvation / noisy neighbor issues**: A single client consuming an unfair share of system resources (CPU, memory, database connections), degrading performance for other users.
- **Cascading Failures**: Unchecked spikes in traffic bringing down downstream microservices.
- **Uncontrolled Costs**: High API infrastructure costs (e.g. paying for server compute, DB queries, or third-party APIs) driven by rogue clients or bugs.

Rate limiting solves this by enforcing thresholds on clients, returning a standard `HTTP 429 Too Many Requests` status code when limits are exceeded.

---

## Architecture
The system scales incrementally across the following tiers:
1. **In-Memory Store (Single Instance)**: Fast, non-persistent, local state.
2. **Concurrent In-Memory Store**: Handles safety, race conditions, and thread locks.
3. **Distributed Store (Redis)**: Uses Redis as a shared database for state synchronization across multiple scaled API nodes behind a Load Balancer (Nginx/HAProxy).

---

## Algorithms
We will implement and compare three classic rate-limiting algorithms:

### Fixed Window
*(To be implemented in Phase 2)*
- **Concept**: Divides time into fixed-size windows (e.g. 1 minute) and tracks request count per client per window.
- **Pros/Cons**: Simple to implement and low memory footprint, but suffers from the **boundary burst problem** at window transitions (allowing up to 2x the limit in a short span).

### Sliding Window
*(To be implemented in Phase 3)*
- **Concept**: Tracks timestamps of requests within a sliding window interval relative to the current moment.
- **Pros/Cons**: Solves the boundary burst problem, but consumes significantly more memory since all timestamps must be stored.

### Token Bucket
*(To be implemented in Phase 4)*
- **Concept**: Tokens are added to a bucket at a constant fill rate. Each incoming request consumes a token. If the bucket is empty, the request is dropped.
- **Pros/Cons**: Smoothly handles burst traffic up to the bucket capacity while maintaining a steady-state average rate limit.

---

## Redis Architecture
*(To be implemented in Phase 7/8)*
Details on the distributed architecture using Redis, sentinel patterns, and performance optimizations.

---

## Load Testing
*(To be implemented in Phase 5)*
Details on using `k6` to benchmark the system under various levels of load.

---

## Benchmark Results
*(To be populated as tests run)*
Actual empirical metrics measured using `k6`.

---

## Failure Experiments
*(To be documented in Phase 9)*
Results from simulating network splits, Redis crashes, and slow responses.

---

## Trade-offs
Summary of memory usage, computational overhead, correctness, and implementation complexity across all tested configurations.

---

## What I Learned
Key insights gained during the construction of these rate limiters.

---

## How to Run

### Phase 1 Setup
Prerequisites: Python 3.11+

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn src.main:app --reload
   ```
5. Verify the API:
   - Open browser or make request to `http://127.0.0.1:8000/api/test`

---

## Future Improvements
Potential enhancements to turn this lab into a fully resilient production-grade rate-limiting library/service.
