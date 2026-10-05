# Retrieval fix after the browser test (2 Oct 2026)

**Problem.** In the browser test, «ما هو أول باب في الفقه؟» and «ما الفرق بين الطاهر والطهور؟» failed because the right passages were never given to the model:
- the word «باب» matched hadith-referencing footnotes;
- «الطاهر» did not match «طاهر»;
- the answer to «أول باب» is the book's structure, which no passage states.

**Changes** (`retrieval.py`):
1. Light stemming: strip و ف ب ل ك and ال.
2. Question-frame words removed from the keyword query.
3. Pure hadith-referencing footnotes ranked lower (weight 0.3).
4. Dense search with BGE-M3 (Ollama, local; embeddings cached in `cache_embeddings.json`).
5. Hybrid: reciprocal-rank fusion of keyword and dense rankings.
6. The anchor's table of contents added as one citable passage.

**Result** (`retrieval_test.py` → `results.md`): a correct page in the top 8 for 11/11 questions, ranked first in all 11. The step-3 BM25 managed 10/11, and its first correct passage was ranked 2nd–4th for three questions.

**End to end** (demo server, Gemma 4 E4B): both failed questions now answered with citations. «الفرق بين الطاهر والطهور» now gives both definitions, an example, and Ibn Taymiyya's two-kinds view, attributed, labelled «أقوال مختلفة».

**Costs:**
- Slower answers: 49–75 s, because the passages are longer and the answers fuller.
- One answer included a loosely related sentence; this still needs the support judge.

**Limits:** 11 questions, one chapter. Turath's own search (`turath_find`) was tried with fixed key terms in one call. That isn't a fair test of it, since it is built for an AI model that refines its terms over several calls.
