import httpx
import time

def run_test():
    url = "http://127.0.0.1:8000/api/test"
    print(f"Sending 11 requests sequentially to {url}...\n")
    
    for i in range(1, 12):
        try:
            response = httpx.get(url)
            limit = response.headers.get("X-RateLimit-Limit", "N/A")
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            reset = response.headers.get("X-RateLimit-Reset", "N/A")
            
            # Convert Unix reset timestamp to a readable time format
            reset_readable = time.strftime('%H:%M:%S', time.localtime(int(reset))) if reset != "N/A" else "N/A"
            
            print(f"Request {i:2d} | Status: {response.status_code} | Limit: {limit} | Remaining: {remaining} | Resets at: {reset_readable}")
        except Exception as e:
            print(f"Request {i:2d} | Failed to connect: {e}")

if __name__ == "__main__":
    run_test()
