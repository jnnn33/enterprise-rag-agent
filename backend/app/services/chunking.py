import re


class TextChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 80) -> None:
        if chunk_size < 50:
            raise ValueError("chunk_size must be at least 50")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be between 0 and chunk_size - 1")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            hard_end = min(start + self.chunk_size, len(normalized))
            end = self._find_boundary(normalized, start, hard_end)
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(normalized):
                break
            start = max(end - self.overlap, start + 1)
        return chunks

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    @staticmethod
    def _find_boundary(text: str, start: int, hard_end: int) -> int:
        if hard_end >= len(text):
            return len(text)

        minimum = start + (hard_end - start) // 2
        boundary_chars = ("\n", "。", "！", "？", ".", "!", "?", "；", ";")
        candidates = [text.rfind(char, minimum, hard_end) for char in boundary_chars]
        best = max(candidates)
        return best + 1 if best >= minimum else hard_end

