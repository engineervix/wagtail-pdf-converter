from unittest.mock import MagicMock, patch

import pytest

from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.services.converter import HybridPDFConverter


@pytest.fixture
def mock_ai_backend():
    backend = MagicMock()
    backend.convert_pdf_to_elements.return_value = [
        HeadingElement(type="heading", level=1, text="Title"),
        ParagraphElement(type="paragraph", text="Body"),
    ]
    return backend


class TestConvertPdfToElements:
    def test_single_pass_returns_elements(self, mock_ai_backend):
        with patch(
            "wagtail_pdf_converter.services.converter.get_ai_backend",
            return_value=mock_ai_backend,
        ):
            converter = HybridPDFConverter()
            # Stub the image pipeline to avoid real extraction/AI calls.
            converter.image_processor = MagicMock()
            converter.image_processor.extract_and_upload_images.return_value = ([], 0)

            elements, metrics = converter.convert_pdf_to_elements(
                pdf_bytes=b"%PDF-1.4 fake",
                collection_name="Extracted Images",
            )

        assert elements[0].type == "heading"
        assert elements[1].type == "paragraph"
        mock_ai_backend.convert_pdf_to_elements.assert_called_once()
        assert "total_pages" in metrics

    def test_image_report_passed_to_backend(self, mock_ai_backend):
        report = [{"page": 1, "image_name": "img.png", "url": "/media/x.png", "image_hash": "h1"}]
        with patch(
            "wagtail_pdf_converter.services.converter.get_ai_backend",
            return_value=mock_ai_backend,
        ):
            converter = HybridPDFConverter()
            converter.image_processor = MagicMock()
            converter.image_processor.extract_and_upload_images.return_value = (report, 1)

            converter.convert_pdf_to_elements(
                pdf_bytes=b"%PDF-1.4 fake",
                collection_name="Extracted Images",
            )

        # The backend must receive the image report so it can reference hashes.
        _, kwargs = mock_ai_backend.convert_pdf_to_elements.call_args
        assert kwargs.get("image_report") == report or report in mock_ai_backend.convert_pdf_to_elements.call_args.args

    def test_empty_result_falls_back_to_paragraph(self, mock_ai_backend):
        mock_ai_backend.convert_pdf_to_elements.return_value = []
        with patch(
            "wagtail_pdf_converter.services.converter.get_ai_backend",
            return_value=mock_ai_backend,
        ):
            converter = HybridPDFConverter()
            converter.image_processor = MagicMock()
            converter.image_processor.extract_and_upload_images.return_value = ([], 0)

            elements, _ = converter.convert_pdf_to_elements(
                pdf_bytes=b"%PDF-1.4 fake",
                collection_name="Extracted Images",
            )

        assert len(elements) == 1
        assert elements[0].type == "paragraph"
