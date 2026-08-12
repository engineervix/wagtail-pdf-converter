from wagtail_pdf_converter.elements import (
    CodeElement,
    ImageElement,
    ListElement,
    QuoteElement,
    TableElement,
)
from wagtail_pdf_converter.mapper import StreamFieldMapper, default_registry


class TestPhase2Converters:
    def setup_method(self):
        self.mapper = StreamFieldMapper(default_registry())

    def test_image_converter_emits_hash_reference(self):
        el = ImageElement(type="image", image_hash="hash123", alt="A chart")
        block_name, value = self.mapper.map_with_fallback("image", el)
        assert block_name == "image"
        # The converter is pure (no DB): it passes through the hash + alt so the
        # loader can resolve the actual Image object.
        assert value["image_hash"] == "hash123"
        assert value["alt"] == "A chart"

    def test_quote_converter(self):
        el = QuoteElement(type="quote", text="To be", attribution="Shakespeare")
        block_name, value = self.mapper.map_with_fallback("quote", el)
        assert block_name == "quote"
        assert value["text"] == "To be"
        assert value["attribution"] == "Shakespeare"

    def test_code_converter(self):
        el = CodeElement(type="code", code="print(1)", language="python")
        block_name, value = self.mapper.map_with_fallback("code", el)
        assert block_name == "code"
        assert value["code"] == "print(1)"
        assert value["language"] == "python"

    def test_table_converter(self):
        el = TableElement(type="table", header=["A", "B"], rows=[["1", "2"]])
        block_name, value = self.mapper.map_with_fallback("table", el)
        assert block_name == "table"
        assert value["header"] == ["A", "B"]
        assert value["rows"] == [["1", "2"]]

    def test_list_converter_unordered(self):
        el = ListElement(type="list", ordered=False, items=["a", "b"])
        block_name, value = self.mapper.map_with_fallback("list", el)
        assert block_name == "list"
        assert value["ordered"] is False
        assert value["items"] == ["a", "b"]
