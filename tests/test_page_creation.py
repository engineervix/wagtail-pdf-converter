import pytest

from wagtail.models import Page

from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.mapper import MapperRegistry, StreamFieldMapper
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
        """A block name the page's StreamField doesn't define (e.g. from a
        custom mapper) must be routed to paragraph, not silently dropped by
        Wagtail's StreamBlock. PDFPage has no 'hero' block, so this exercises
        the loader's own fallback, not the mapper's."""
        root = Page.objects.get(id=2)
        registry = MapperRegistry()
        registry.register("heading", lambda el: ("hero", el.text))
        mapper = StreamFieldMapper(registry)

        elements = [HeadingElement(type="heading", level=1, text="orphan")]

        page = create_page_from_elements(
            title="Fallback Test",
            elements=elements,
            parent=root,
            page_model=PDFPage,
            mapper=mapper,
        )
        assert [b.block_type for b in page.body] == ["paragraph"]
        assert str(page.body[0].value) == "orphan"

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

    def test_new_page_is_created_as_draft(self):
        """AI-derived content must be reviewed before it goes live, not published on creation."""
        root = Page.objects.get(id=2)
        page = create_page_from_elements(
            title="Draft Check",
            elements=[ParagraphElement(type="paragraph", text="x")],
            parent=root,
            page_model=PDFPage,
        )
        assert page.live is False
        assert page.has_unpublished_changes is True
        assert Page.objects.get(pk=page.pk).live is False
