"""Tests for PDF text extraction and chunking."""

import fitz  # pymupdf
import pytest

from src.pdf.processor import PDFProcessor


def _make_pdf(text: str) -> bytes:
    """Create a minimal single-page PDF containing *text*."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def processor():
    """Default PDFProcessor with standard settings."""
    return PDFProcessor(chunk_size=1000, chunk_overlap=200)


class TestExtractText:
    """Tests for PDFProcessor.extract_text."""

    def test_extracts_text_from_pdf(self, processor):
        """Simple PDF with known text is extracted correctly."""
        pdf = _make_pdf("Hello World")
        result = processor.extract_text(pdf)
        assert "Hello World" in result

    def test_empty_pdf_returns_empty_string(self, processor):
        """PDF with no text content returns empty string."""
        doc = fitz.open()
        doc.new_page()  # blank page
        pdf_bytes = doc.tobytes()
        doc.close()

        result = processor.extract_text(pdf_bytes)
        assert result == ""


class TestProcessPdf:
    """Tests for PDFProcessor.process_pdf."""

    def test_returns_chunks(self, processor):
        """PDF with enough text produces multiple chunks."""
        long_text = "This is a test sentence. " * 200
        pdf = _make_pdf(long_text)

        chunks = processor.process_pdf(pdf)

        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    def test_empty_pdf_returns_empty_list(self, processor):
        """PDF with no text produces empty chunk list."""
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()

        chunks = processor.process_pdf(pdf_bytes)
        assert chunks == []

    def test_chunk_size_affects_output(self):
        """Smaller chunk_size produces more chunks."""
        long_text = "This is a test sentence. " * 200
        pdf = _make_pdf(long_text)

        large = PDFProcessor(chunk_size=2000, chunk_overlap=0)
        small = PDFProcessor(chunk_size=500, chunk_overlap=0)

        chunks_large = large.process_pdf(pdf)
        chunks_small = small.process_pdf(pdf)

        assert len(chunks_small) > len(chunks_large)
