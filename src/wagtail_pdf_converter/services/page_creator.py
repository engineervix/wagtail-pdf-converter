"""
Loader: turns a mapped element stream into a saved Wagtail Page.

This is the only layer that touches the database. The mapper produces
``(block_name, value)`` tuples (pure, no DB); this module assembles them into a
StreamField value and places the new page under the resolved parent, following
the tree-placement pattern from Wagtail's Page.add_child.
"""

import logging

from typing import Any

from django.utils.text import slugify
from wagtail.images import get_image_model
from wagtail.models import Page

from ..elements import Element
from ..mapper import StreamFieldMapper


logger = logging.getLogger(__name__)


def resolve_image_by_hash(image_hash: str):
    """Resolve an extracted image's content hash to its Wagtail Image object."""
    Image = get_image_model()
    return Image.objects.filter(file_hash=image_hash).first()


def create_page_from_elements(
    title: str,
    elements: list[Element],
    parent: Page,
    page_model: type[Page],
    mapper: StreamFieldMapper | None = None,
    user: Any | None = None,
) -> Page:
    """
    Create a Wagtail Page of ``page_model`` under ``parent`` from typed elements.

    The element stream is mapped to (block_name, value) tuples, any block name
    not present on the page's StreamField is routed to the paragraph fallback
    (so content is never silently dropped), then the page is added to the tree
    and a revision is saved.
    """
    mapper = mapper or StreamFieldMapper()
    block_tuples = mapper.map(elements)

    page = page_model(title=title, slug=slugify(title))
    if user is not None:
        page.owner = user

    stream_field = page_model._meta.get_field("body")
    allowed_block_names = set(stream_field.stream_block.child_blocks.keys())

    safe_tuples: list[tuple[str, Any]] = []
    for block_name, value in block_tuples:
        # Image blocks carry a content-hash reference that must be resolved to
        # the stored Image object. If the page model has no image block, or the
        # hash cannot be resolved, fall back to a paragraph so nothing is lost.
        if block_name == "image" and "image" in allowed_block_names:
            resolved = resolve_image_by_hash(value.get("image_hash", ""))
            if resolved is not None:
                safe_tuples.append(("image", resolved))
                continue
            logger.warning(
                "Could not resolve image hash '%s'; routing to paragraph fallback.",
                value.get("image_hash"),
            )
            block_name, value = fallback_from_value(value.get("alt", ""))
        elif block_name not in allowed_block_names:
            logger.warning(
                "Block type '%s' is not registered on %s.body; routing to paragraph fallback.",
                block_name,
                page_model.__name__,
            )
            block_name, value = fallback_from_value(value)
        safe_tuples.append((block_name, value))

    page.body = safe_tuples

    parent.add_child(instance=page)
    page.save_revision(user=user)
    return page


def fallback_from_value(value: Any) -> tuple[str, Any]:
    """Coerce an unmapped block value back to a plain paragraph tuple."""
    text = value if isinstance(value, str) else str(value)
    return ("paragraph", text)


def convert_pdf_to_page(
    document: Any,
    parent: Page,
    page_model: type[Page],
    title: str | None = None,
    user: Any | None = None,
    mapper: StreamFieldMapper | None = None,
    converter: Any | None = None,
) -> Page:
    """
    High-level orchestrator: convert a Wagtail Document (PDF) into a Page.

    Runs the image-extraction pipeline and AI element conversion, then loads the
    resulting element stream into a new page of ``page_model`` under ``parent``.
    Returns the created page.

    ``converter`` is injectable for testing; defaults to a real HybridPDFConverter.
    """
    from ..constants import EXTRACTED_IMAGES_COLLECTION_NAME

    if converter is None:
        from .converter import HybridPDFConverter

        converter = HybridPDFConverter()

    with document.open_file() as f:
        pdf_bytes = f.read()

    elements, _metrics = converter.convert_pdf_to_elements(
        pdf_bytes=pdf_bytes,
        collection_name=EXTRACTED_IMAGES_COLLECTION_NAME,
        document_id=document.pk,
    )

    return create_page_from_elements(
        title=title or document.title,
        elements=elements,
        parent=parent,
        page_model=page_model,
        mapper=mapper,
        user=user,
    )
