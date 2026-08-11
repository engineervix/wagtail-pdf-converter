import json

from wagtail_pdf_converter.elements import HeadingElement, ParagraphElement
from wagtail_pdf_converter.services.backends.gemini import GeminiBackend


class TestParseElementsResponse:
    """Deterministic parse/validation of AI JSON output (no network)."""

    def _backend(self):
        # Bypass __init__ (which requires an API key and network client).
        return GeminiBackend.__new__(GeminiBackend)

    def test_parses_valid_json_object(self):
        backend = self._backend()
        payload = json.dumps(
            {
                "elements": [
                    {"type": "heading", "level": 1, "text": "Title"},
                    {"type": "paragraph", "text": "Body"},
                ]
            }
        )
        elements = backend.parse_elements_response(payload)
        assert isinstance(elements[0], HeadingElement)
        assert isinstance(elements[1], ParagraphElement)

    def test_strips_markdown_code_fence(self):
        backend = self._backend()
        payload = "```json\n" + json.dumps({"elements": [{"type": "paragraph", "text": "x"}]}) + "\n```"
        elements = backend.parse_elements_response(payload)
        assert elements[0].text == "x"

    def test_invalid_json_returns_fallback_paragraph(self):
        backend = self._backend()
        elements = backend.parse_elements_response("this is not json")
        assert len(elements) == 1
        assert isinstance(elements[0], ParagraphElement)
        assert "this is not json" in elements[0].text

    def test_long_invalid_response_is_truncated_in_fallback(self):
        """A malformed response shouldn't dump an unbounded blob into a page."""
        backend = self._backend()
        garbage = "not json " * 1000  # ~9000 chars
        elements = backend.parse_elements_response(garbage)
        assert len(elements) == 1
        assert len(elements[0].text) < len(garbage)
        assert elements[0].text.endswith("[truncated]")

    def test_schema_violation_returns_fallback_paragraph(self):
        backend = self._backend()
        # heading level out of range -> validation error -> fallback
        payload = json.dumps({"elements": [{"type": "heading", "level": 99, "text": "Bad"}]})
        elements = backend.parse_elements_response(payload)
        assert len(elements) == 1
        assert isinstance(elements[0], ParagraphElement)

    def test_empty_elements_returns_fallback(self):
        backend = self._backend()
        elements = backend.parse_elements_response(json.dumps({"elements": []}))
        assert len(elements) == 1
        assert isinstance(elements[0], ParagraphElement)

    def test_missing_elements_key_returns_fallback(self):
        """Valid JSON, but not shaped like {"elements": [...]}."""
        backend = self._backend()
        elements = backend.parse_elements_response(json.dumps({"foo": "bar"}))
        assert len(elements) == 1
        assert isinstance(elements[0], ParagraphElement)

    def test_bare_list_json_returns_fallback(self):
        """A bare JSON list (not wrapped in {"elements": ...}) isn't the expected shape."""
        backend = self._backend()
        payload = json.dumps([{"type": "paragraph", "text": "x"}])
        elements = backend.parse_elements_response(payload)
        assert len(elements) == 1
        assert isinstance(elements[0], ParagraphElement)
