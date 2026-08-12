"""
Default StreamField block kit for PDF-derived pages.

Block names here correspond 1:1 with the default mapper registry so that every
element the AI can emit has a registered block — Wagtail silently drops block
types a StreamField does not recognise, so the kit and the registry must agree.

Each block renders through an overridable template carrying a stable
``pdf-page-*`` CSS class, so a site can restyle PDF-derived content without
overriding the templates, or override a template for full control.
"""

from wagtail import blocks
from wagtail.blocks.struct_block import StructValue
from wagtail.images.blocks import ImageChooserBlock


class PDFImageBlock(ImageChooserBlock):
    """An image chooser that renders wrapped in a ``pdf-page-image`` figure."""

    class Meta:
        template = "wagtail_pdf_converter/blocks/image.html"


class HeadingValue(StructValue):
    """A heading's value, exposing the ``<hN>`` tag for its level."""

    @property
    def level_tag(self) -> str:
        level = self.get("level", 2)
        # Clamp to a valid heading range so a bad value can't produce h0/h7.
        level = max(1, min(6, level))
        return f"h{level}"


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    level = blocks.ChoiceBlock(
        choices=[(i, f"H{i}") for i in range(1, 7)],
        default=2,
    )

    class Meta:
        icon = "title"
        template = "wagtail_pdf_converter/blocks/heading.html"
        value_class = HeadingValue


class QuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock()
    attribution = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"
        template = "wagtail_pdf_converter/blocks/quote.html"


class CodeBlock(blocks.StructBlock):
    code = blocks.TextBlock()
    language = blocks.CharBlock(required=False)

    class Meta:
        icon = "code"
        template = "wagtail_pdf_converter/blocks/code.html"


class TableBlock(blocks.StructBlock):
    header = blocks.ListBlock(blocks.CharBlock(), required=False)
    rows = blocks.ListBlock(blocks.ListBlock(blocks.CharBlock()), required=False)

    class Meta:
        icon = "table"
        template = "wagtail_pdf_converter/blocks/table.html"


class ListBlock(blocks.StructBlock):
    ordered = blocks.BooleanBlock(required=False, default=False)
    items = blocks.ListBlock(blocks.CharBlock())

    class Meta:
        icon = "list-ul"
        template = "wagtail_pdf_converter/blocks/list.html"


class PDFStreamBlock(blocks.StreamBlock):
    """Default block set for a page body built from a converted PDF."""

    heading = HeadingBlock()
    paragraph = blocks.RichTextBlock(template="wagtail_pdf_converter/blocks/paragraph.html")
    image = PDFImageBlock()
    quote = QuoteBlock()
    code = CodeBlock()
    table = TableBlock()
    list = ListBlock()

    class Meta:
        block_counts = None
