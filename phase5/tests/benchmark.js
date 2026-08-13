import http from 'k6/http';
import { sleep } from 'k6';

// k6 Options: Can be overridden by CLI args (e.g. k6 run --vus 100 --duration 10s)
export const options = {
  vus: 1,
  duration: '10s',
  thresholds: {
    http_req_failed: ['rate>=0'], // Do not fail the test on 429s
  },
};

export default function () {
  http.get('http://127.0.0.1:8000/api/test');
  
  // A tiny sleep to prevent VUs from completely locking the local event loop,
  // while still generating high-concurrency traffic.
  sleep(0.01); 
}
