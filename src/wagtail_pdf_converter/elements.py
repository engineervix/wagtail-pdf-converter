"""
Typed intermediate representation of PDF content.

The AI backend converts a PDF into a list of these typed elements (via
schema-constrained structured JSON output). The mapper then turns each element
into a ``(block_name, value)`` StreamField tuple. This module is the single
authoritative definition of the element stream contract shared by both sides.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class BaseElement(BaseModel):
    """Base class for all element types. Subclass and set a ``type`` Literal."""

    type: str


class HeadingElement(BaseElement):
    type: Literal["heading"]
    level: int = Field(ge=1, le=6)
    text: str


class ParagraphElement(BaseElement):
    type: Literal["paragraph"]
    text: str


class ImageElement(BaseElement):
    """An image pulled from the PDF.

    ``image_hash`` is the SHA-1 content hash assigned when the image was
    extracted and stored as a Wagtail Image (see ``add_image_to_wagtail_collection``);
    it is the stable identity the loader uses to resolve the element to the
    existing Image object. ``alt`` is the AI-generated accessible description.
    """

    type: Literal["image"]
    image_hash: str
    alt: str = ""


class QuoteElement(BaseElement):
    type: Literal["quote"]
    text: str
    attribution: str | None = None


class CodeElement(BaseElement):
    type: Literal["code"]
    code: str
    language: str = ""


class TableElement(BaseElement):
    type: Literal["table"]
    header: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ListElement(BaseElement):
    type: Literal["list"]
    ordered: bool = False
    items: list[str] = Field(default_factory=list)


class GenericElement(BaseElement):
    """Catch-all for an element type with no registered model.

    Carries whatever fields the AI emitted (extras allowed) so the content
    survives to the mapper, which routes it to the paragraph fallback.
    """

    model_config = {"extra": "allow"}

    type: str

    @property
    def text(self) -> str:
        """Best-effort plain-text view used by the paragraph fallback."""
        extra = self.model_extra or {}
        for field in ("text", "content", "value", "alt"):
            value = extra.get(field)
            if isinstance(value, str) and value:
                return value
        return self.model_dump_json()


# The built-in element models, in registration order.
_BUILTIN_ELEMENT_MODELS: list[type[BaseElement]] = [
    HeadingElement,
    ParagraphElement,
    ImageElement,
    QuoteElement,
    CodeElement,
    TableElement,
    ListElement,
]

# type-string -> model class, for every registered element type.
_ELEMENT_REGISTRY: dict[str, type[BaseElement]] = {}

# type-string -> human-readable description for the AI prompt (custom types only).
_ELEMENT_DESCRIPTIONS: dict[str, str] = {}


def _register(model: type[BaseElement], description: str | None = None) -> None:
    field = model.model_fields["type"]
    # For Literal["x"], read the literal argument; for a plain str default, use it.
    literal_args = getattr(field.annotation, "__args__", None)
    type_value = literal_args[0] if literal_args else field.default
    _ELEMENT_REGISTRY[str(type_value)] = model
    if description:
        _ELEMENT_DESCRIPTIONS[str(type_value)] = description


def register_element_type(model: type[BaseElement], description: str | None = None) -> None:
    """
    Register a custom element type so it parses and appears in the AI schema.

    The model must subclass ``BaseElement`` and define ``type: Literal["..."]``.
    Re-registering the same ``type`` replaces the previous model. ``description``
    is a one-line, AI-facing explanation of when to emit the type (what content it
    represents and which fields it needs); it is appended to the conversion prompt.
    """
    if not (isinstance(model, type) and issubclass(model, BaseElement)):
        raise TypeError("register_element_type expects a BaseElement subclass")
    _register(model, description)


def custom_element_prompt_lines() -> list[str]:
    """Prompt lines describing each custom-registered element type, in order."""
    return [f"- `{type_str}`: {desc}" for type_str, desc in _ELEMENT_DESCRIPTIONS.items()]


def _reset_element_registry_for_tests() -> None:
    """Restore the registry to just the built-in types. Used by tests."""
    _ELEMENT_REGISTRY.clear()
    _ELEMENT_DESCRIPTIONS.clear()
    for model in _BUILTIN_ELEMENT_MODELS:
        _register(model)


# Initialise with the built-ins.
_reset_element_registry_for_tests()

# Backwards-compatible alias: the element type used across the codebase.
# Parsing routes via the registry, so this is the common base, not a closed union.
Element = BaseElement


def parse_elements(raw: list[dict[str, Any]]) -> list[BaseElement]:
    """
    Validate a raw list of element dicts into typed element models.

    Each item is routed to the registered model for its ``type``; a registered
    type with invalid fields raises ``ValidationError``. An item whose ``type``
    has no registered model becomes a :class:`GenericElement` (content preserved)
    rather than raising, so unknown content is never dropped here — the mapper's
    fallback handles it downstream.
    """
    parsed: list[BaseElement] = []
    for item in raw:
        if not isinstance(item, dict):
            item = {"type": "paragraph", "text": str(item)}
        type_str = item.get("type")
        model = _ELEMENT_REGISTRY.get(type_str) if isinstance(type_str, str) else None
        parsed.append((model or GenericElement).model_validate(item))
    return parsed


class DocumentElements(BaseModel):
    """The top-level structured payload returned by the AI backend."""

    elements: list[BaseElement]

    @classmethod
    def _registry_schema(cls) -> dict[str, Any]:
        """Build the elements schema from the registered element models."""
        item_schemas = [
            model.model_json_schema()
            for model in _ELEMENT_REGISTRY.values()
            if model is not GenericElement  # the catch-all is never advertised to the AI
        ]
        return {
            "type": "object",
            "properties": {
                "elements": {"type": "array", "items": {"anyOf": item_schemas}},
            },
            "required": ["elements"],
        }

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        # Single source of truth: the schema always reflects the registered
        # element types, whether called directly or via response_json_schema().
        return cls._registry_schema()

    @classmethod
    def response_json_schema(cls) -> dict[str, Any]:
        """
        JSON Schema passed to Gemini's ``response_json_schema`` config.

        Built from the registered element models, so custom types registered via
        ``register_element_type`` are included and the AI is constrained to emit
        only known types.
        """
        return cls._registry_schema()
