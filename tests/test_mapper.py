from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.mapper import MapperRegistry, StreamFieldMapper


class TestMapperRegistry:
    def test_register_and_lookup(self):
        registry = MapperRegistry()
        registry.register("heading", lambda el: ("heading", el.text))
        converter = registry.get("heading")
        assert converter is not None

    def test_lookup_unknown_returns_none(self):
        registry = MapperRegistry()
        assert registry.get("nonexistent") is None

    def test_fallback_is_used_for_unknown_type(self):
        registry = MapperRegistry()
        fallback = registry.get_fallback()
        element = ParagraphElement(type="paragraph", text="orphan content")
        block_name, value = fallback(element)
        assert block_name == "paragraph"


class TestStreamFieldMapper:
    def test_maps_heading_to_block_tuple(self):
        mapper = StreamFieldMapper()
        elements = [HeadingElement(type="heading", level=2, text="Section")]
        result = mapper.map(elements)
        assert result == [("heading", "Section")]

    def test_maps_paragraph_to_block_tuple(self):
        mapper = StreamFieldMapper()
        elements = [ParagraphElement(type="paragraph", text="Body text")]
        result = mapper.map(elements)
        assert result == [("paragraph", "Body text")]

    def test_unknown_element_falls_back_to_paragraph(self):
        """Content must never be silently dropped (Wagtail drops unknown block types)."""
        mapper = StreamFieldMapper()
        # Simulate an element type with no registered converter.
        element = ParagraphElement(type="paragraph", text="unmapped stuff")
        result = mapper.map_with_fallback("nonexistent_type", element)
        assert result == ("paragraph", "unmapped stuff")

    def test_map_preserves_order(self):
        mapper = StreamFieldMapper()
        elements = [
            HeadingElement(type="heading", level=1, text="Title"),
            ParagraphElement(type="paragraph", text="First"),
            ParagraphElement(type="paragraph", text="Second"),
        ]
        result = mapper.map(elements)
        assert [t for t, _ in result] == ["heading", "paragraph", "paragraph"]
