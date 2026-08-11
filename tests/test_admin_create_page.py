from unittest.mock import MagicMock

import pytest

from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse

from wagtail_pdf_converter.elements import ParagraphElement

from .testproject.testapp.models import CustomDocument, PDFPage


@pytest.mark.django_db
class TestCreatePageFromDocumentView:
    def _make_document(self):
        return CustomDocument.objects.create(
            title="Report",
            file=ContentFile(b"%PDF-1.4 fake", name="report.pdf"),
        )

    def _settings(self, **overrides):
        base = {
            "ENABLE_PAGE_CREATION": True,
            "PAGE_CREATION_MODEL": "tests.testproject.testapp.models.PDFPage",
            "PAGE_CREATION_PARENT_ID": 2,
        }
        base.update(overrides)
        return override_settings(WAGTAIL_PDF_CONVERTER=base)

    def test_disabled_by_default_redirects_with_error(self, client_superuser):
        document = self._make_document()
        url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
        client_superuser.post(url, follow=True)
        # Feature flag off -> redirected, no page created
        assert PDFPage.objects.count() == 0

    def test_creates_page_when_enabled(self, client_superuser, monkeypatch):
        document = self._make_document()
        elements = [ParagraphElement(type="paragraph", text="Hello world.")]
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (elements, {})

        # Inject the converter at the orchestrator boundary.
        monkeypatch.setattr(
            "wagtail_pdf_converter.admin_views._build_converter",
            lambda: mock_converter,
        )

        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            client_superuser.post(url, follow=True)

        assert PDFPage.objects.count() == 1
        page = PDFPage.objects.first()
        assert page.title == "Report"
        assert page.get_parent().pk == 2

    def test_get_shows_confirmation_page(self, client_superuser):
        """GET renders a confirmation page; it does NOT create a page."""
        document = self._make_document()
        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            response = client_superuser.get(url)
        assert response.status_code == 200
        assert PDFPage.objects.count() == 0
        assert b"Create page" in response.content or b"create" in response.content.lower()

    def test_get_disabled_shows_error_not_confirm(self, client_superuser):
        document = self._make_document()
        url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
        client_superuser.get(url, follow=True)
        assert PDFPage.objects.count() == 0
