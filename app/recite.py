"""Recitation matching, the same logic as web/js/features.js (align), for the evaluation on recorded clips.

A recognised word matches the expected word when, after normalising and stripping a prefix, they are equal or at least
75% similar (edit distance). Up to 3 expected words may be skipped to find a match; a word the recogniser split in two
is joined. Anything else is a wrong word.
"""
from .retrieval import stem
from .textnorm import normalise


def sim(a, b):
    if a == b:
        return 1.0
    m, n = len(a), len(b)
    if not m or not n:
        return 0.0
    d = [[i] + [0] * n for i in range(m + 1)]
    d[0] = list(range(n + 1))
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return 1 - d[m][n] / max(m, n)


def key(w):
    n = normalise(w)
    return stem(n) if n else ""


def align(expected, heard):
    """expected, heard: lists of words -> (states per expected word: ok|wrong|skip|pending, words said instead)."""
    E = [key(w) for w in expected]
    H = [k for k in (key(w) for w in heard) if k]
    st, said = ["pending"] * len(E), [""] * len(E)
    i, h = 0, 0
    while h < len(H) and i < len(E):
        x = H[h]
        if sim(x, E[i]) >= 0.75 or (len(x) > 2 and x in E[i] and len(x) / len(E[i]) > 0.6):
            st[i] = "ok"
            i += 1
            h += 1
            continue
        j = 1
        while j <= 3 and i + j < len(E) and sim(x, E[i + j]) < 0.75:
            j += 1
        if j <= 3 and i + j < len(E):
            for k in range(i, i + j):
                st[k] = "skip"
            st[i + j] = "ok"
            i += j + 1
            h += 1
            continue
        if h + 1 < len(H) and sim(x + H[h + 1], E[i]) >= 0.75:
            st[i] = "ok"
            i += 1
            h += 2
            continue
        st[i], said[i] = "wrong", heard[h] if h < len(heard) else ""
        i += 1
        h += 1
    return st, said
