from unittest.mock import MagicMock, patch

from wagtail_pdf_converter.elements import ParagraphElement
from wagtail_pdf_converter.services.converter import HybridPDFConverter


def P(text):
    return ParagraphElement(type="paragraph", text=text)


class TestChunkedElementDedup:
    def test_chunked_conversion_dedups_seam(self):
        # Two chunks share an overlap element "shared" at the seam.
        backend = MagicMock()
        backend.convert_pdf_to_elements.side_effect = [
            [P("page1"), P("shared")],
            [P("shared"), P("page2")],
        ]

        with patch(
            "wagtail_pdf_converter.services.converter.get_ai_backend",
            return_value=backend,
        ):
            converter = HybridPDFConverter()
            converter.image_processor = MagicMock()
            converter.image_processor.extract_and_upload_images.return_value = ([], 0)
            # Force the chunked path and a controlled 2-chunk split.
            converter.split_pdf_into_chunks = MagicMock(return_value=[b"chunk1", b"chunk2"])

            elements, _ = converter.convert_pdf_to_elements(
                pdf_bytes=b"%PDF-1.4 fake",
                collection_name="Extracted Images",
                force_chunking=True,
            )

        texts = [e.text for e in elements]
        assert texts == ["page1", "shared", "page2"]

    def test_chunked_conversion_preserves_non_seam_duplicates(self):
        # "ref" appears in both chunks but NOT at the seam -> must be preserved.
        backend = MagicMock()
        backend.convert_pdf_to_elements.side_effect = [
            [P("ref"), P("end-of-chunk-1")],
            [P("start-of-chunk-2"), P("ref")],
        ]

        with patch(
            "wagtail_pdf_converter.services.converter.get_ai_backend",
            return_value=backend,
        ):
            converter = HybridPDFConverter()
            converter.image_processor = MagicMock()
            converter.image_processor.extract_and_upload_images.return_value = ([], 0)
            converter.split_pdf_into_chunks = MagicMock(return_value=[b"chunk1", b"chunk2"])

            elements, _ = converter.convert_pdf_to_elements(
                pdf_bytes=b"%PDF-1.4 fake",
                collection_name="Extracted Images",
                force_chunking=True,
            )

        texts = [e.text for e in elements]
        assert texts == ["ref", "end-of-chunk-1", "start-of-chunk-2", "ref"]
