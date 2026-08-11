"""
Maps the typed element stream to StreamField block tuples.

A converter is a callable taking an element and returning a
``(block_name, value)`` tuple. The registry maps element ``type`` strings to
converters and supplies a paragraph fallback so that unmapped content is never
silently dropped — Wagtail's ``StreamBlock`` discards block types it does not
recognise, so every element must resolve to a registered block name.
"""

from collections.abc import Callable
from typing import Any

from .elements import (
    CodeElement,
    Element,
    ImageElement,
    ListElement,
    QuoteElement,
    TableElement,
)


Converter = Callable[[Element], tuple[str, Any]]

FALLBACK_BLOCK = "paragraph"


def _heading_converter(element: Element) -> tuple[str, Any]:
    return ("heading", element.text)


def _paragraph_converter(element: Element) -> tuple[str, Any]:
    return ("paragraph", element.text)


def _image_converter(element: ImageElement) -> tuple[str, Any]:
    # Pure: pass the content hash + alt through so the loader can resolve the
    # already-stored Wagtail Image by hash (no DB access here).
    return ("image", {"image_hash": element.image_hash, "alt": element.alt})


def _quote_converter(element: QuoteElement) -> tuple[str, Any]:
    return ("quote", {"text": element.text, "attribution": element.attribution})


def _code_converter(element: CodeElement) -> tuple[str, Any]:
    return ("code", {"code": element.code, "language": element.language})


def _table_converter(element: TableElement) -> tuple[str, Any]:
    return ("table", {"header": element.header, "rows": element.rows})


def _list_converter(element: ListElement) -> tuple[str, Any]:
    return ("list", {"ordered": element.ordered, "items": element.items})


class MapperRegistry:
    """Registry of element-type -> converter, with a guaranteed fallback."""

    def __init__(self, fallback: Converter | None = None) -> None:
        self._converters: dict[str, Converter] = {}
        self._fallback = fallback or _paragraph_converter

    def register(self, element_type: str, converter: Converter) -> None:
        self._converters[element_type] = converter

    def get(self, element_type: str) -> Converter | None:
        return self._converters.get(element_type)

    def get_fallback(self) -> Converter:
        return self._converters.get(FALLBACK_BLOCK, self._fallback)


def default_registry() -> MapperRegistry:
    registry = MapperRegistry()
    registry.register("heading", _heading_converter)
    registry.register("paragraph", _paragraph_converter)
    registry.register("image", _image_converter)
    registry.register("quote", _quote_converter)
    registry.register("code", _code_converter)
    registry.register("table", _table_converter)
    registry.register("list", _list_converter)
    return registry


class StreamFieldMapper:
    """Converts a list of elements to StreamField (block_name, value) tuples."""

    def __init__(self, registry: MapperRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def map_with_fallback(self, element_type: str, element: Element) -> tuple[str, Any]:
        converter = self.registry.get(element_type) or self.registry.get_fallback()
        return converter(element)

    def map(self, elements: list[Element]) -> list[tuple[str, Any]]:
        return [self.map_with_fallback(el.type, el) for el in elements]
