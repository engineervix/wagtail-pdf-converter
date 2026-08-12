from wagtail_pdf_converter.elements import HeadingElement, ListElement, ParagraphElement
from wagtail_pdf_converter.services.converter import dedup_chunk_boundary


def P(text):
    return ParagraphElement(type="paragraph", text=text)


class TestDedupChunkBoundary:
    def test_no_overlap_returns_all(self):
        accumulated = [P("a"), P("b")]
        new = [P("c"), P("d")]
        assert dedup_chunk_boundary(accumulated, new) == [P("c"), P("d")]

    def test_exact_overlap_at_seam_is_removed(self):
        # Chunk 1 ends with "x", chunk 2 starts with "x" (the shared overlap page).
        accumulated = [P("a"), P("x")]
        new = [P("x"), P("b")]
        assert dedup_chunk_boundary(accumulated, new) == [P("b")]

    def test_multi_element_overlap_removed(self):
        accumulated = [P("a"), P("x"), P("y")]
        new = [P("x"), P("y"), P("b")]
        assert dedup_chunk_boundary(accumulated, new) == [P("b")]

    def test_type_mismatch_is_not_a_duplicate(self):
        # Same text but different type -> not a duplicate.
        accumulated = [P("intro")]
        new = [HeadingElement(type="heading", level=2, text="intro"), P("body")]
        result = dedup_chunk_boundary(accumulated, new)
        assert len(result) == 2
        assert isinstance(result[0], HeadingElement)

    def test_does_not_dedup_beyond_the_seam(self):
        # A duplicate that is NOT at the immediate seam must be preserved.
        # "a" appears in accumulated but not as the trailing edge matching new[0].
        accumulated = [P("a"), P("b")]
        new = [P("c"), P("a")]  # "a" repeats later in new chunk - legit content
        result = dedup_chunk_boundary(accumulated, new)
        assert result == [P("c"), P("a")]

    def test_empty_new_chunk(self):
        assert dedup_chunk_boundary([P("a")], []) == []

    def test_empty_accumulated(self):
        assert dedup_chunk_boundary([], [P("a")]) == [P("a")]

    def test_whole_chunk_is_duplicate(self):
        accumulated = [P("a"), P("x"), P("y")]
        new = [P("x"), P("y")]
        assert dedup_chunk_boundary(accumulated, new) == []

    def test_list_elements_dedup_by_content(self):
        accumulated = [P("a"), ListElement(type="list", ordered=False, items=["1", "2"])]
        new = [ListElement(type="list", ordered=False, items=["1", "2"]), P("b")]
        assert dedup_chunk_boundary(accumulated, new) == [P("b")]
