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

    def test_position_drifted_duplicate_is_removed(self):
        # The AI segments the shared overlap page differently in each chunk
        # call. "shared1"/"shared2" repeat, but chunk 2 has a new element
        # ahead of them, so they do not land at new[0].
        accumulated = [P("intro"), P("shared1"), P("shared2")]
        new = [P("newfirst"), P("shared1"), P("shared2"), P("continues")]
        result = dedup_chunk_boundary(accumulated, new)
        assert result == [P("newfirst"), P("continues")]

    def test_isolated_duplicate_run_of_one_away_from_seam_is_preserved(self):
        # A single matching element away from the true seam is too easily a
        # legitimate recurring line, for example a boilerplate cross-reference.
        # Only a run of 2+ elements counts as a real seam duplicate when it is
        # not anchored at accumulated[-1]/new[0].
        accumulated = [P("a"), P("b"), P("c")]
        new = [P("newfirst"), P("b"), P("continues")]
        result = dedup_chunk_boundary(accumulated, new)
        assert result == [P("newfirst"), P("b"), P("continues")]

    def test_window_bounds_how_far_back_matches_are_considered(self):
        # "run1"/"run2" recur several elements before accumulated's tail, too
        # far back to plausibly be the overlap page. A small window leaves
        # them alone, even though they form a matching run of 2.
        accumulated = [P("run1"), P("run2"), P("mid1"), P("mid2"), P("mid3")]
        new = [P("run1"), P("run2"), P("tail")]
        result = dedup_chunk_boundary(accumulated, new, window=3)
        assert result == [P("run1"), P("run2"), P("tail")]
