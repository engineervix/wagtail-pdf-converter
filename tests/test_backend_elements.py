import json

from types import SimpleNamespace

from pydantic import BaseModel, ConfigDict

from wagtail_pdf_converter.elements import HeadingElement, ImageElement, ParagraphElement
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


class TestFormatImageReportForElements:
    """A 40-character SHA-1 hash is hard for the model to copy back exactly,
    and gets worse the more images a document has. The model is given a
    short index for each image instead."""

    def _backend(self):
        return GeminiBackend.__new__(GeminiBackend)

    def test_empty_report(self):
        text, index_to_hash = self._backend()._format_image_report_for_elements([])
        assert text == "No images were found in this document."
        assert index_to_hash == {}

    def test_exposes_index_not_hash(self):
        report = [
            {"page": 1, "description": "A chart", "image_hash": "a" * 40},
            {"page": 2, "description": "A photo", "image_hash": "b" * 40},
        ]
        text, index_to_hash = self._backend()._format_image_report_for_elements(report)

        assert "INDEX: 1" in text
        assert "INDEX: 2" in text
        assert "a" * 40 not in text
        assert "b" * 40 not in text
        assert index_to_hash == {"1": "a" * 40, "2": "b" * 40}


class TestResolveImageIndexes:
    """Translates the model's index reference back to the real content hash,
    the other half of the index scheme above."""

    def _backend(self):
        return GeminiBackend.__new__(GeminiBackend)

    def test_translates_known_index(self):
        elements = [ImageElement(type="image", image_hash="1", alt="A chart")]
        resolved = self._backend()._resolve_image_indexes(elements, {"1": "a" * 40})
        assert resolved[0].image_hash == "a" * 40

    def test_leaves_unknown_index_untouched(self):
        """An index the model got wrong is left as-is. It will not resolve to
        a stored Image either way, so the existing paragraph fallback in
        create_page_from_elements already covers it."""
        elements = [ImageElement(type="image", image_hash="99", alt="A chart")]
        resolved = self._backend()._resolve_image_indexes(elements, {"1": "a" * 40})
        assert resolved[0].image_hash == "99"

    def test_leaves_a_real_hash_untouched(self):
        """If the model writes a real hash anyway, ignoring the instructions,
        an index string can never match it (short digits vs. 40 hex chars),
        so it passes through unchanged."""
        elements = [ImageElement(type="image", image_hash="c" * 40, alt="A chart")]
        resolved = self._backend()._resolve_image_indexes(elements, {"1": "a" * 40})
        assert resolved[0].image_hash == "c" * 40

    def test_non_image_elements_are_untouched(self):
        elements = [ParagraphElement(type="paragraph", text="hi")]
        resolved = self._backend()._resolve_image_indexes(elements, {"1": "a" * 40})
        assert resolved == elements

    def test_custom_image_type_without_image_hash_does_not_crash(self):
        """A project can register its own model under the "image" type (see
        register_element_type in elements.py). One with no image_hash field
        must not crash the translation step."""
        el = SimpleNamespace(type="image", ref="whatever")
        resolved = self._backend()._resolve_image_indexes([el], {"1": "a" * 40})
        assert resolved[0] is el

    def test_frozen_custom_image_type_is_not_mutated_in_place(self):
        """A custom image type registered as a frozen model must still get
        translated. This builds a new element instead of setting the field
        in place."""

        class FrozenImage(BaseModel):
            model_config = ConfigDict(frozen=True)
            type: str = "image"
            image_hash: str

        el = FrozenImage(image_hash="1")
        resolved = self._backend()._resolve_image_indexes([el], {"1": "a" * 40})
        assert resolved[0].image_hash == "a" * 40
        assert resolved[0] is not el
