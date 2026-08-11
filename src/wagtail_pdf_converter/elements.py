"""
Typed intermediate representation of PDF content.

The AI backend converts a PDF into a list of these typed elements (via
schema-constrained structured JSON output). The mapper then turns each element
into a ``(block_name, value)`` StreamField tuple. This module is the single
authoritative definition of the element stream contract shared by both sides.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class HeadingElement(BaseModel):
    type: Literal["heading"]
    level: int = Field(ge=1, le=6)
    text: str


class ParagraphElement(BaseModel):
    type: Literal["paragraph"]
    text: str


class ImageElement(BaseModel):
    """An image pulled from the PDF.

    ``image_hash`` is the SHA-1 content hash assigned when the image was
    extracted and stored as a Wagtail Image (see ``add_image_to_wagtail_collection``);
    it is the stable identity the loader uses to resolve the element to the
    existing Image object. ``alt`` is the AI-generated accessible description.
    """

    type: Literal["image"]
    image_hash: str
    alt: str = ""


class QuoteElement(BaseModel):
    type: Literal["quote"]
    text: str
    attribution: str | None = None


class CodeElement(BaseModel):
    type: Literal["code"]
    code: str
    language: str = ""


class TableElement(BaseModel):
    type: Literal["table"]
    header: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ListElement(BaseModel):
    type: Literal["list"]
    ordered: bool = False
    items: list[str] = Field(default_factory=list)


# Discriminated union on the ``type`` field so parsing routes each raw dict to
# the correct element model.
Element = Annotated[
    HeadingElement | ParagraphElement | ImageElement | QuoteElement | CodeElement | TableElement | ListElement,
    Field(discriminator="type"),
]


class DocumentElements(BaseModel):
    """The top-level structured payload returned by the AI backend."""

    elements: list[Element]

    @classmethod
    def response_json_schema(cls) -> dict[str, Any]:
        """JSON Schema passed to Gemini's ``response_json_schema`` config."""
        return cls.model_json_schema()


def parse_elements(raw: list[dict[str, Any]]) -> list[Element]:
    """Validate a raw list of element dicts into typed element models."""
    return DocumentElements(elements=raw).elements  # type: ignore[arg-type]
