"""Linking regression tests. Need data/books (not in git); skipped when the texts are absent."""
import pytest

from app import books as B
from app import ingest
from app.textnorm import split_notes, split_page

pytestmark = pytest.mark.skipif(not (B.BOOKS / "12216" / "full.json").exists(), reason="book texts not present")


@pytest.fixture(scope="module")
def iq():
    return ingest.walk(12216)


def test_marker_note_comes_from_its_own_page(iq):
    """The prep bug: a note was looked up on the page where its unit started. Units cross pages; numbers restart."""
    _, _, markers, notes_by_pg = iq
    crossing = [m for m in markers if m["pg"] != m["unit_pg"]]
    assert len(crossing) > 50, "expected many markers on a later page than their unit's start"
    for m in markers:
        assert m["note"] == notes_by_pg[m["pg"]].get(m["n"], ""), m
    # the old lookup would have given a different note for most of the crossing markers
    old_differs = sum(notes_by_pg.get(m["unit_pg"], {}).get(m["n"], "") != m["note"] for m in crossing)
    assert old_differs > len(crossing) // 2


def test_every_marker_has_note_text(iq):
    _, _, markers, _ = iq
    assert markers and all(m["note"] for m in markers)


def test_continuation_joined():
    notes = {1: split_notes("(١) أول الحاشية =\n"), 2: split_notes("= تتمة الحاشية\n(١) حاشية ثانية")}
    ingest.join_continuations(notes)
    assert notes[1][1] == "أول الحاشية تتمة الحاشية"
    assert 0 not in notes[2] and notes[2][1] == "حاشية ثانية"


def test_split_page():
    body, notes = split_page("نص (١)\n_________\n(١) حاشية")
    assert body == "نص (١)" and split_notes(notes) == {1: "حاشية"}


def test_chapter_counts_stable():
    study, stats, _ = ingest.build()
    assert [c["id"] for c in study["chapters"]] == ["water", "vessels", "istinja"]
    for cid, s in stats.items():
        assert s["iq_linked"] == s["iq_notes"] > 0
        assert s["iq_methods_agree"] / s["iq_both_methods"] >= 0.8
        assert s["mumti_linked"] >= 0.7 * s["mumti_headings"]
