import hashlib

from io import BytesIO

import pytest

from PIL import Image as PILImage
from wagtail.images import get_image_model
from wagtail.models import Page

from wagtail_pdf_converter.elements import HeadingElement, ImageElement, ParagraphElement
from wagtail_pdf_converter.services.page_creator import create_page_from_elements
from wagtail_pdf_converter.utils import add_image_to_wagtail_collection

from .testproject.testapp.models import PDFPage


Image = get_image_model()


def _png_bytes() -> bytes:
    """Generate a small valid PNG in-memory."""
    img = PILImage.new("RGB", (10, 10), color=(200, 30, 30))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
class TestImageHashResolution:
    def _make_image(self, name="page_1_img_0.png"):
        # Use the real pipeline helper so the stored Image gets a content hash.
        data = _png_bytes()
        add_image_to_wagtail_collection(image_data=data, image_name=name)
        return hashlib.sha1(data, usedforsecurity=False).hexdigest()

    def test_resolves_image_hash_to_image_object(self):
        image_hash = self._make_image()
        assert Image.objects.filter(file_hash=image_hash).exists()

        root = Page.objects.get(id=2)
        page = create_page_from_elements(
            title="With Image",
            elements=[ImageElement(type="image", image_hash=image_hash, alt="A chart")],
            parent=root,
            page_model=PDFPage,
        )
        image_block = page.body[0]
        assert image_block.block_type == "image"
        # The block value must be the resolved Image, not the raw hash dict.
        assert image_block.value.pk is not None
        assert image_block.value.file_hash == image_hash

    def test_unknown_image_hash_falls_back_to_paragraph(self):
        """An image the loader cannot resolve must not silently vanish."""
        root = Page.objects.get(id=2)
        page = create_page_from_elements(
            title="Missing Image",
            elements=[ImageElement(type="image", image_hash="doesnotexist", alt="ghost")],
            parent=root,
            page_model=PDFPage,
        )
        # Falls back to a paragraph carrying the alt text so content survives.
        assert page.body[0].block_type == "paragraph"
        assert "ghost" in str(page.body[0].value)

    def test_mixed_stream_with_image(self):
        image_hash = self._make_image()
        root = Page.objects.get(id=2)
        page = create_page_from_elements(
            title="Mixed",
            elements=[
                HeadingElement(type="heading", level=1, text="Report"),
                ImageElement(type="image", image_hash=image_hash, alt="Fig 1"),
                ParagraphElement(type="paragraph", text="Caption text."),
            ],
            parent=root,
            page_model=PDFPage,
        )
        assert [b.block_type for b in page.body] == ["heading", "image", "paragraph"]
