import pytest

from wagtail_pdf_converter.blocks import (
    CodeBlock,
    ListBlock,
    PDFStreamBlock,
    QuoteBlock,
    TableBlock,
)


@pytest.mark.django_db
class TestBlockStyling:
    """Each kit block renders with a stable, overridable pdf-page-* CSS class."""

    def test_quote_block_renders_class(self):
        block = QuoteBlock()
        html = block.render({"text": "To be or not to be", "attribution": "Shakespeare"})
        assert "pdf-page-quote" in html
        assert "To be or not to be" in html
        assert "Shakespeare" in html

    def test_code_block_renders_class_and_language(self):
        block = CodeBlock()
        html = block.render({"code": "print(1)", "language": "python"})
        assert "pdf-page-code" in html
        assert "python" in html
        assert "print(1)" in html

    def test_table_block_renders_class(self):
        block = TableBlock()
        html = block.render({"header": ["A", "B"], "rows": [["1", "2"]]})
        assert "pdf-page-table" in html
        assert "A" in html
        assert "1" in html

    def test_list_block_renders_class_and_ordered(self):
        block = ListBlock()
        html = block.render({"ordered": True, "items": ["one", "two"]})
        assert "pdf-page-list" in html
        assert "one" in html

    def test_heading_and_paragraph_have_classes(self):
        stream = PDFStreamBlock()
        # Build a real StreamValue so .render() works as it does on a page.
        value = stream.to_python(
            [
                {"type": "heading", "value": {"text": "Section", "level": 2}},
                {"type": "paragraph", "value": "<p>Body</p>"},
            ]
        )
        html = stream.render(value)
        assert "pdf-page-heading" in html
        assert "pdf-page-paragraph" in html
        # The heading renders the correct <hN> tag for its level.
        assert "<h2" in html

    def test_image_block_has_class(self):
        from io import BytesIO

        from django.core.files.images import ImageFile
        from PIL import Image as PILImage
        from wagtail.images import get_image_model

        # Create a real image so the block renders the figure wrapper.
        img = PILImage.new("RGB", (10, 10), color=(0, 128, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        Image = get_image_model()
        wagtail_image = Image.objects.create(
            title="test",
            file=ImageFile(BytesIO(buf.getvalue()), name="test.png"),
        )

        block = PDFStreamBlock().child_blocks["image"]
        html = block.render(wagtail_image)
        assert "pdf-page-image" in html
        assert "<figure" in html

    def test_image_block_empty_is_safe(self):
        stream = PDFStreamBlock()
        # Rendering an empty stream (no image) must not raise.
        assert stream.render([]) is not None
