from wagtail.admin.panels import FieldPanel
from wagtail.documents.models import AbstractDocument
from wagtail.fields import StreamField
from wagtail.models import Page

from wagtail_pdf_converter.blocks import PDFStreamBlock
from wagtail_pdf_converter.models import PDFConversionMixin


class CustomDocument(PDFConversionMixin, AbstractDocument):  # type: ignore[django-manager-missing]
    pass


class PDFPage(Page):
    """A page whose body is built from converted PDF elements."""

    body = StreamField(PDFStreamBlock(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
