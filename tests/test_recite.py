from app.recite import align

LINE = "وَهِيَ ارْتِفَاعُ الحَدَثِ وَمَا فِي مَعْنَاهُ وَزَوَالُ الخَبَثِ".split()


def test_exact_recitation_all_ok():
    st, _ = align(LINE, "وهي ارتفاع الحدث وما في معناه وزوال الخبث".split())
    assert st == ["ok"] * len(LINE)


def test_tashkeel_and_hamza_differences_ignored():
    st, _ = align(LINE, "وهى إرتفاع الحدث وما فى معناة وزوال الخبث".split())
    assert st == ["ok"] * len(LINE)


def test_skipped_word_flagged():
    st, _ = align(LINE, "وهي ارتفاع الحدث وما معناه وزوال الخبث".split())
    assert st[4] == "skip" and st.count("ok") == len(LINE) - 1


def test_wrong_word_flagged_with_what_was_said():
    st, said = align(LINE, "وهي ارتفاع النجس وما في معناه وزوال الخبث".split())
    assert st[2] == "wrong" and said[2] == "النجس"


def test_partial_recitation_leaves_rest_pending():
    st, _ = align(LINE, "وهي ارتفاع".split())
    assert st[:2] == ["ok", "ok"] and set(st[2:]) == {"pending"}
