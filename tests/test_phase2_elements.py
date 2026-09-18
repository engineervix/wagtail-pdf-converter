from wagtail_pdf_converter.elements import (
    DocumentElements,
    ImageElement,
    ListElement,
    QuoteElement,
    TableElement,
    parse_elements,
)


class TestPhase2ElementModels:
    def test_image_element(self):
        el = ImageElement(type="image", image_hash="abc123", alt="A chart")
        assert el.type == "image"
        assert el.image_hash == "abc123"
        assert el.alt == "A chart"

    def test_quote_element(self):
        el = QuoteElement(type="quote", text="To be or not to be", attribution="Shakespeare")
        assert el.type == "quote"
        assert el.attribution == "Shakespeare"

    def test_quote_attribution_optional(self):
        el = QuoteElement(type="quote", text="A quote")
        assert el.attribution is None

    def test_code_element(self):
        el = __import__("wagtail_pdf_converter.elements", fromlist=["CodeElement"]).CodeElement(
            type="code", code="print('hi')", language="python"
        )
        assert el.type == "code"
        assert el.language == "python"

    def test_table_element(self):
        el = TableElement(
            type="table",
            header=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )
        assert el.header == ["Name", "Age"]
        assert len(el.rows) == 2

    def test_list_element(self):
        el = ListElement(type="list", ordered=False, items=["one", "two"])
        assert el.ordered is False
        assert el.items == ["one", "two"]

    def test_parse_mixed_stream_discriminates(self):
        raw = [
            {"type": "image", "image_hash": "h1", "alt": "pic"},
            {"type": "quote", "text": "q"},
            {"type": "table", "header": ["a"], "rows": [["1"]]},
            {"type": "list", "ordered": True, "items": ["x"]},
        ]
        elements = parse_elements(raw)
        assert isinstance(elements[0], ImageElement)
        assert isinstance(elements[1], QuoteElement)
        assert isinstance(elements[2], TableElement)
        assert isinstance(elements[3], ListElement)

    def test_schema_includes_new_types(self):
        schema = DocumentElements.model_json_schema()
        schema_str = str(schema)
        for t in ["image", "quote", "table", "list", "code"]:
            assert t in schema_str
