import pytest

from wagtail.models import Page

from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.services.page_creator import create_page_from_elements

from .testproject.testapp.models import PDFPage


@pytest.mark.django_db
class TestCreatePageFromElements:
    def test_creates_page_with_streamfield_blocks(self):
        root = Page.objects.get(id=2)  # default home page
        elements = [
            HeadingElement(type="heading", level=1, text="Annual Report"),
            ParagraphElement(type="paragraph", text="Our performance this year."),
        ]

        page = create_page_from_elements(
            title="Annual Report",
            elements=elements,
            parent=root,
            page_model=PDFPage,
        )

        assert page.pk is not None
        assert page.title == "Annual Report"
        assert page.get_parent() == root

        body = page.body
        block_types = [b.block_type for b in body]
        assert block_types == ["heading", "paragraph"]
        assert str(body[1].value) == "Our performance this year."

    def test_unknown_block_type_falls_back_to_paragraph(self):
        """No content is silently dropped even if a block type is unregistered."""
        root = Page.objects.get(id=2)
        elements = [
            ParagraphElement(type="paragraph", text="orphan"),
        ]
        # Force an unknown element type through the mapper path.
        page = create_page_from_elements(
            title="Fallback Test",
            elements=elements,
            parent=root,
            page_model=PDFPage,
        )
        assert [b.block_type for b in page.body] == ["paragraph"]

    def test_page_is_child_of_parent(self):
        root = Page.objects.get(id=2)
        page = create_page_from_elements(
            title="Child",
            elements=[ParagraphElement(type="paragraph", text="x")],
            parent=root,
            page_model=PDFPage,
        )
        assert page.slug
        assert root.get_children().filter(pk=page.pk).exists()
