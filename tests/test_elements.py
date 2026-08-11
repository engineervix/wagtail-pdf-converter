import pytest

from pydantic import ValidationError

from wagtail_pdf_converter.elements import (
    DocumentElements,
    HeadingElement,
    ParagraphElement,
    parse_elements,
)


class TestElementModels:
    def test_heading_element(self):
        el = HeadingElement(type="heading", level=2, text="Hello")
        assert el.type == "heading"
        assert el.level == 2
        assert el.text == "Hello"

    def test_paragraph_element(self):
        el = ParagraphElement(type="paragraph", text="Some text")
        assert el.type == "paragraph"
        assert el.text == "Some text"

    def test_heading_level_bounds(self):
        with pytest.raises(ValidationError):
            HeadingElement(type="heading", level=0, text="x")
        with pytest.raises(ValidationError):
            HeadingElement(type="heading", level=7, text="x")

    def test_document_elements_roundtrip(self):
        doc = DocumentElements(
            elements=[
                HeadingElement(type="heading", level=1, text="Title"),
                ParagraphElement(type="paragraph", text="Body"),
            ]
        )
        assert len(doc.elements) == 2

    def test_parse_elements_from_json_list(self):
        raw = [
            {"type": "heading", "level": 1, "text": "Title"},
            {"type": "paragraph", "text": "Body"},
        ]
        elements = parse_elements(raw)
        assert elements[0].type == "heading"
        assert elements[1].type == "paragraph"

    def test_parse_elements_discriminates_on_type(self):
        raw = [{"type": "heading", "level": 3, "text": "Sub"}]
        elements = parse_elements(raw)
        assert isinstance(elements[0], HeadingElement)
        assert elements[0].level == 3

    def test_response_json_schema_available(self):
        schema = DocumentElements.model_json_schema()
        assert "properties" in schema
        assert "elements" in schema["properties"]
