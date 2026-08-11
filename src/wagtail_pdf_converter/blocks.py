"""
Default StreamField block kit for PDF-derived pages.

Block names here correspond 1:1 with the default mapper registry so that every
element the AI can emit has a registered block — Wagtail silently drops block
types a StreamField does not recognise, so the kit and the registry must agree.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class QuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock()
    attribution = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"


class CodeBlock(blocks.StructBlock):
    code = blocks.TextBlock()
    language = blocks.CharBlock(required=False)

    class Meta:
        icon = "code"


class TableBlock(blocks.StructBlock):
    header = blocks.ListBlock(blocks.CharBlock(), required=False)
    rows = blocks.ListBlock(blocks.ListBlock(blocks.CharBlock()), required=False)

    class Meta:
        icon = "table"


class ListBlock(blocks.StructBlock):
    ordered = blocks.BooleanBlock(required=False, default=False)
    items = blocks.ListBlock(blocks.CharBlock())

    class Meta:
        icon = "list-ul"


class PDFStreamBlock(blocks.StreamBlock):
    """Default block set for a page body built from a converted PDF."""

    heading = blocks.CharBlock(form_classname="title")
    paragraph = blocks.RichTextBlock()
    image = ImageChooserBlock()
    quote = QuoteBlock()
    code = CodeBlock()
    table = TableBlock()
    list = ListBlock()

    class Meta:
        block_counts = None
