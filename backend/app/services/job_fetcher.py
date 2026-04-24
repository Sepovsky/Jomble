import requests


class JobHTMLFetcher:
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }

    def fetch_html(self, url: str) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self._load_with_requests(url)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_timeout(1500)
                html = page.content()
                final_url = page.url
                title = page.title()
                browser.close()

            return {
                "url": url,
                "final_url": final_url,
                "title": title,
                "html": html,
                "source": "playwright",
            }
        except Exception:
            return self._load_with_requests(url)

    def _load_with_requests(self, url: str) -> dict:
        response = requests.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return {
            "url": url,
            "final_url": str(response.url),
            "title": None,
            "html": response.text,
            "source": "requests",
        }
