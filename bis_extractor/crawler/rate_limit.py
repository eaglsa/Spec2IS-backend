import time
import threading
from bis_extractor.config import CRAWL_DELAY_SECONDS

class RateLimiter:
    def __init__(self, delay=CRAWL_DELAY_SECONDS):
        self.delay = delay
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.last_request_time = time.time()

rate_limiter = RateLimiter()
