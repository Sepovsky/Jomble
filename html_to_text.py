from bs4 import BeautifulSoup
import re
from job_fetcher import JobHTMLFetcher



class HTMLToTextConverter:
    # Removed unconditionally by tag name (includes semantic structural elements)
    REMOVE_TAGS = [
        "script", "style", "noscript", "svg", "img",
        "video", "audio", "iframe", "canvas",
        "header", "footer", "nav",
    ]

    # Matched as whole words against individual CSS class tokens and id tokens.
    # Using whole-word matching avoids false positives like "header-compact" or
    # "posting-header" triggering on "header".
    NOISY_WORD_PATTERNS = {
        "cookie", "consent", "banner", "newsletter", "subscribe",
        "breadcrumb", "social", "share", "login", "signup", "popup", "modal",
    }

    def convert(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(self.REMOVE_TAGS):
            tag.decompose()

        to_remove = []
        for tag in soup.find_all(True):
            raw = tag.attrs or {}
            classes = raw.get("class", [])
            class_list = classes if isinstance(classes, list) else classes.split()
            id_val = str(raw.get("id", ""))
            # Split hyphen/underscore-separated tokens so "main-banner" → {"main","banner"}
            tokens: set[str] = set()
            for token in class_list + [id_val]:
                tokens.update(re.split(r"[-_]", token.lower()))

            if tokens & self.NOISY_WORD_PATTERNS:
                to_remove.append(tag)

        for tag in to_remove:
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return self._normalize_text(text)

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        lines = [self._clean_line(line) for line in text.splitlines()]
        lines = [line for line in lines if line]

        deduped = []
        prev = None
        for line in lines:
            if line != prev:
                deduped.append(line)
            prev = line

        return "\n".join(deduped)

    def _clean_line(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":

    fetcher = JobHTMLFetcher()
    converter = HTMLToTextConverter()

    # url = "https://jobs.lever.co/gomaterials/735f7252-fdb2-4a8f-8994-eaa694a5e091"
    url = "https://reffie.me/jobs/swe-ml-toronto"
    url = 'https://ats.rippling.com/pythian/jobs/815b0d16-5f55-41e6-8c97-119b716750bd?src=LinkedIn'

    page = fetcher.fetch_html(url)
    clean_text = converter.convert(page["html"])

    print(clean_text)