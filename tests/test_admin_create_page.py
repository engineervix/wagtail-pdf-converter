from unittest.mock import MagicMock

import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from wagtail.models import GroupPagePermission, Page

from wagtail_pdf_converter.elements import ParagraphElement

from .testproject.testapp.models import CustomDocument, PDFPage


User = get_user_model()


@pytest.mark.django_db
class TestCreatePageFromDocumentView:
    def _make_document(self):
        return CustomDocument.objects.create(
            title="Report",
            file=ContentFile(b"%PDF-1.4 fake", name="report.pdf"),
        )

    def _make_editor(self, username, can_add_subpage_on=None):
        """A staff user with Wagtail admin access but no page permissions,
        optionally granted 'add' on a specific page (e.g. the configured parent)."""
        user = User.objects.create_user(username=username, password="password", is_staff=True)  # noqa: S106
        group = Group.objects.create(name=f"{username}-group")
        group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
        user.groups.add(group)
        if can_add_subpage_on is not None:
            GroupPagePermission.objects.create(group=group, page=can_add_subpage_on, permission_type="add")
        return user

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

    def test_denied_without_add_subpage_permission(self, client, monkeypatch):
        """Admin access alone must not be enough; the user needs page-tree
        add permission on the configured parent, same as Wagtail's own
        page-create view enforces. The converter is mocked so a real AI/network
        failure can't be mistaken for the permission check doing its job."""
        document = self._make_document()
        user = self._make_editor("no-page-perms")
        client.force_login(user)

        elements = [ParagraphElement(type="paragraph", text="Hello world.")]
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (elements, {})
        monkeypatch.setattr(
            "wagtail_pdf_converter.admin_views._build_converter",
            lambda: mock_converter,
        )

        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            client.post(url, follow=True)

        assert PDFPage.objects.count() == 0
        mock_converter.convert_pdf_to_elements.assert_not_called()

    def test_get_denied_without_add_subpage_permission(self, client):
        document = self._make_document()
        user = self._make_editor("no-page-perms-get")
        client.force_login(user)

        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            response = client.get(url)

        assert PDFPage.objects.count() == 0
        assert b"Create page from PDF" not in response.content

    def test_allowed_with_add_subpage_permission(self, client, monkeypatch):
        document = self._make_document()
        parent = Page.objects.get(pk=2)
        user = self._make_editor("has-page-perms", can_add_subpage_on=parent)
        client.force_login(user)

        elements = [ParagraphElement(type="paragraph", text="Hello world.")]
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (elements, {})
        monkeypatch.setattr(
            "wagtail_pdf_converter.admin_views._build_converter",
            lambda: mock_converter,
        )

        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            client.post(url, follow=True)

        assert PDFPage.objects.count() == 1

    def test_non_pdf_document_is_rejected(self, client_superuser, monkeypatch):
        """A non-PDF document must be refused outright, not handed to the AI
        pipeline (which would otherwise happily fabricate a page from it if
        the converter tolerates non-PDF bytes, or crash unclearly if not)."""
        document = CustomDocument.objects.create(
            title="Not a PDF",
            file=ContentFile(b"just some text", name="notes.txt"),
        )
        mock_converter = MagicMock()
        mock_converter.convert_pdf_to_elements.return_value = (
            [ParagraphElement(type="paragraph", text="fabricated")],
            {},
        )
        monkeypatch.setattr(
            "wagtail_pdf_converter.admin_views._build_converter",
            lambda: mock_converter,
        )

        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            client_superuser.post(url, follow=True)

        assert PDFPage.objects.count() == 0
        mock_converter.convert_pdf_to_elements.assert_not_called()

    def test_get_non_pdf_document_shows_error_not_confirm(self, client_superuser):
        document = CustomDocument.objects.create(
            title="Not a PDF",
            file=ContentFile(b"just some text", name="notes.txt"),
        )
        with self._settings():
            url = reverse("wagtail_pdf_converter:create_page", args=[document.id])
            response = client_superuser.get(url, follow=True)

        assert PDFPage.objects.count() == 0
        assert b"Create page from PDF" not in response.content
