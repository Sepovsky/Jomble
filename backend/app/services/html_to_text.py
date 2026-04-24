import re

from bs4 import BeautifulSoup, Tag


class HTMLToTextConverter:
    REMOVE_TAGS = [
        "script", "style", "noscript", "svg", "img",
        "video", "audio", "iframe", "canvas",
        "header", "footer", "nav",
    ]

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
            if not isinstance(tag, Tag):
                continue
            raw = tag.attrs or {}
            classes = raw.get("class", [])
            class_list = classes if isinstance(classes, list) else classes.split()
            id_val = str(raw.get("id", ""))
            tokens: set[str] = set()
            for token in class_list + [id_val]:
                tokens.update(re.split(r"[-_]", token.lower()))
            if tokens & self.NOISY_WORD_PATTERNS:
                to_remove.append(tag)

        for tag in to_remove:
            tag.decompose()

        return self._normalize_text(soup.get_text(separator="\n", strip=True))

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        lines = [self._clean_line(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        deduped: list[str] = []
        prev = None
        for line in lines:
            if line != prev:
                deduped.append(line)
            prev = line
        return "\n".join(deduped)

    def _clean_line(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
