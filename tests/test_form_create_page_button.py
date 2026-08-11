import pytest

from django.core.files.base import ContentFile
from django.test import override_settings

from tests.testproject.testapp.models import CustomDocument
from wagtail_pdf_converter.forms import PDFConverterDocumentForm


class DocumentForm(PDFConverterDocumentForm):
    class Meta(PDFConverterDocumentForm.Meta):
        model = CustomDocument
        fields = "__all__"


def _pdf_document():
    return CustomDocument.objects.create(
        title="Report",
        file=ContentFile(b"%PDF-1.4 fake", name="report.pdf"),
    )


def _enabled(**overrides):
    base = {
        "ENABLE_PAGE_CREATION": True,
        "PAGE_CREATION_MODEL": "tests.testproject.testapp.models.PDFPage",
        "PAGE_CREATION_PARENT_ID": 2,
    }
    base.update(overrides)
    return override_settings(WAGTAIL_PDF_CONVERTER=base)


@pytest.mark.django_db
class TestCreatePageButtonInForm:
    def _actions_html(self, form):
        """Render conversion_actions, or '' if the field was deleted (no buttons)."""
        if "conversion_actions" not in form.fields:
            return ""
        return str(form.fields["conversion_actions"].widget.content)

    def test_button_shown_when_enabled_and_pdf(self):
        document = _pdf_document()
        with _enabled():
            form = DocumentForm(instance=document)
            html = self._actions_html(form)
        assert "create-page" in html
        assert "Create page" in html

    def test_button_hidden_when_disabled(self):
        document = _pdf_document()
        # ENABLE_PAGE_CREATION defaults to False
        form = DocumentForm(instance=document)
        assert "create-page" not in self._actions_html(form)

    def test_button_hidden_when_model_not_configured(self):
        document = _pdf_document()
        with _enabled(PAGE_CREATION_MODEL=None):
            form = DocumentForm(instance=document)
            assert "create-page" not in self._actions_html(form)
