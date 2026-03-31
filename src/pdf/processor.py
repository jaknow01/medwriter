"""PDF text extraction and chunking."""

import fitz  # pymupdf
from llama_index.core.node_parser.text.sentence import SentenceSplitter
from llama_index.core.schema import TextNode


class PDFProcessor:
    """Extracts text from PDF bytes and splits into chunks."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._splitter = SentenceSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract all text from a PDF file given as bytes."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages.append(text)
        doc.close()
        return "\n\n".join(pages)

    def process_pdf(self, pdf_bytes: bytes) -> list[str]:
        """Extract text from PDF and split into chunks."""
        text = self.extract_text(pdf_bytes)
        if not text:
            return []

        node = TextNode(text=text)
        chunks = self._splitter([node])
        return [chunk.text for chunk in chunks if chunk.text.strip()]
