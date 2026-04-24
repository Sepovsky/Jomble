import re

import fitz


class ResumeParser:
    def parse(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        pages = [page.get_text("text") for page in doc if page.get_text("text")]
        doc.close()
        return self._normalize_text("\n".join(pages))

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
