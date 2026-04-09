"""PDF text extraction and chunking."""

import fitz  # pymupdf
from llama_index.core.node_parser.text.sentence import SentenceSplitter
from llama_index.core.node_parser.text.token import TokenTextSplitter
from llama_index.core.node_parser.text.sentence_window import SentenceWindowNodeParser
from llama_index.core.schema import TextNode
from loguru import logger

from src.config.json_config import ChunkerConfig

CHUNKER_REGISTRY: dict[str, type] = {
    "sentence": SentenceSplitter,
    "token": TokenTextSplitter,
    "sentence_window": SentenceWindowNodeParser,
}


class PDFProcessor:
    """Extracts text from PDF bytes and splits into chunks."""

    def __init__(self, chunker_config: ChunkerConfig | None = None):
        """Initialize with chunker configuration.

        Args:
            chunker_config: Chunker type and params. Falls back to SentenceSplitter defaults.
        """
        if chunker_config is None:
            chunker_config = ChunkerConfig()

        chunker_type = chunker_config.type
        chunker_cls = CHUNKER_REGISTRY.get(chunker_type)
        if chunker_cls is None:
            raise ValueError(
                f"Unknown chunker type '{chunker_type}'. "
                f"Available: {', '.join(CHUNKER_REGISTRY.keys())}"
            )

        logger.info(f"Initializing PDF chunker: {chunker_type} with params {chunker_config.params}")
        self._splitter = chunker_cls(**chunker_config.params)

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
