import fitz  # PyMuPDF uses the 'fitz' namespace
from typing import List


class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """
        Extracts raw plain text directly from PDF file bytes.
        """
        text_content = []
        # Open document directly from memory
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                # 'text' layout preserves reading order without formatting noise
                page_text = page.get_text("text")
                if page_text.strip():
                    text_content.append(page_text)

        return "\n".join(text_content)

    @staticmethod
    def chunk_text(
        text: str, chunk_size: int = 500, chunk_overlap: int = 50
    ) -> List[str]:
        """
        Splits raw text into windowed chunks to prepare for embedding generation.
        """
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            # Move the window forward by chunk_size minus overlap
            start += chunk_size - chunk_overlap

        return chunks
