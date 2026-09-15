from playwright.sync_api import sync_playwright

class BrowserClient:
    def __init__(self, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
    def new_page(self):
        return self.context.new_page()

    def close(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()
