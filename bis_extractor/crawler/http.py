import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from bis_extractor.config import RETRY_LIMIT

class HttpClient:
    def __init__(self, base_url: str = ""):
        self.client = httpx.Client(
            base_url=base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            },
            verify=False,
            timeout=30.0
        )

    @retry(stop=stop_after_attempt(RETRY_LIMIT), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get(self, url: str, params: dict = None):
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response

    @retry(stop=stop_after_attempt(RETRY_LIMIT), wait=wait_exponential(multiplier=1, min=2, max=10))
    def post(self, url: str, json: dict = None, data: dict = None):
        response = self.client.post(url, json=json, data=data)
        response.raise_for_status()
        return response
        
    def close(self):
        self.client.close()
