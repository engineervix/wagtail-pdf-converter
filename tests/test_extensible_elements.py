from typing import Literal

import pytest

from wagtail_pdf_converter.elements import (
    BaseElement,
    DocumentElements,
    ParagraphElement,
    _reset_element_registry_for_tests,
    parse_elements,
    register_element_type,
)
from wagtail_pdf_converter.mapper import StreamFieldMapper, default_registry


class CalloutElement(BaseElement):
    """A custom element type registered by a site."""

    type: Literal["callout"]
    text: str
    variant: str = "info"


@pytest.fixture(autouse=True)
def clean_registry():
    """Each test starts from the default registry and restores it after."""
    _reset_element_registry_for_tests()
    yield
    _reset_element_registry_for_tests()


class TestExtensibleElements:
    def test_custom_type_parses_after_registration(self):
        register_element_type(CalloutElement)
        elements = parse_elements([{"type": "callout", "text": "Note:", "variant": "warning"}])
        assert isinstance(elements[0], CalloutElement)
        assert elements[0].variant == "warning"

    def test_custom_type_appears_in_response_schema(self):
        register_element_type(CalloutElement)
        schema = DocumentElements.response_json_schema()
        assert "callout" in str(schema)

    def test_unregistered_type_still_falls_back(self):
        # A type the AI emitted that has no registered model -> generic element,
        # preserved for the mapper's paragraph fallback (never dropped).
        elements = parse_elements([{"type": "mystery", "text": "kept"}])
        assert elements[0].type == "mystery"
        assert elements[0].text == "kept"

    def test_custom_type_without_converter_falls_back_to_paragraph(self):
        register_element_type(CalloutElement)
        elements = parse_elements([{"type": "callout", "text": "Pay attention"}])
        mapper = StreamFieldMapper(default_registry())
        # No converter registered for "callout" -> paragraph fallback, content kept.
        result = mapper.map(elements)
        assert result == [("paragraph", "Pay attention")]

    def test_custom_type_with_custom_converter(self):
        register_element_type(CalloutElement)
        registry = default_registry()
        registry.register("callout", lambda el: ("callout", {"text": el.text, "variant": el.variant}))
        mapper = StreamFieldMapper(registry)
        elements = parse_elements([{"type": "callout", "text": "Heads up", "variant": "warning"}])
        result = mapper.map(elements)
        assert result == [("callout", {"text": "Heads up", "variant": "warning"})]

    def test_builtin_types_unaffected(self):
        register_element_type(CalloutElement)
        elements = parse_elements([{"type": "paragraph", "text": "plain"}])
        assert isinstance(elements[0], ParagraphElement)

    def test_description_appears_in_prompt_lines(self):
        register_element_type(CalloutElement, description="A highlighted callout box. Provide text and variant.")
        from wagtail_pdf_converter.elements import custom_element_prompt_lines

        lines = custom_element_prompt_lines()
        assert any("callout" in line and "highlighted callout" in line for line in lines)

    def test_no_custom_types_means_no_extra_prompt_lines(self):
        from wagtail_pdf_converter.elements import custom_element_prompt_lines

        assert custom_element_prompt_lines() == []
