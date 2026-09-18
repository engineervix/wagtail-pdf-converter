from unittest.mock import MagicMock

import pytest

from django.core.files.base import ContentFile
from wagtail.models import Page

from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.services.page_creator import convert_pdf_to_page

from .testproject.testapp.models import CustomDocument, PDFPage


@pytest.mark.django_db
class TestConvertPdfToPage:
    def _make_document(self):
        return CustomDocument.objects.create(
            title="Annual Report",
            file=ContentFile(b"%PDF-1.4 fake", name="annual-report.pdf"),
        )

    def test_creates_page_from_document(self):
        document = self._make_document()
        root = Page.objects.get(id=2)

        elements = [
            HeadingElement(type="heading", level=1, text="Annual Report"),
            ParagraphElement(type="paragraph", text="Body text."),
        ]

        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (elements, {"total_pages": 1})

        page = convert_pdf_to_page(document, parent=root, page_model=PDFPage, converter=mock_converter)

        assert page.pk is not None
        assert page.title == "Annual Report"
        assert [b.block_type for b in page.body] == ["heading", "paragraph"]
        mock_converter.convert_pdf_to_elements.assert_called_once()

    def test_title_defaults_to_document_title(self):
        document = self._make_document()
        root = Page.objects.get(id=2)
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (
            [ParagraphElement(type="paragraph", text="x")],
            {},
        )
        page = convert_pdf_to_page(document, parent=root, page_model=PDFPage, converter=mock_converter)
        assert page.title == "Annual Report"

    def test_title_override(self):
        document = self._make_document()
        root = Page.objects.get(id=2)
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (
            [ParagraphElement(type="paragraph", text="x")],
            {},
        )
        page = convert_pdf_to_page(
            document, parent=root, page_model=PDFPage, title="Custom Title", converter=mock_converter
        )
        assert page.title == "Custom Title"
