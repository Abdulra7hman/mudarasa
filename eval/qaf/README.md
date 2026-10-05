# Head-to-head with Qaf (qaf.ai), the named alternative

**Protocol**
- The same 20 probe questions go to both systems. They come from `prep/research_qaf/qaf_probe_questions.csv`, which is kept out of git because Qaf's answers quote whole paragraphs.
- Each probe tests one capability (أ–ي in the sheet).

**Qaf**
- Entered by hand on qaf.ai.
- Screenshots saved as `eval/qaf/QAFnn.png` (gitignored).
- Each result scored in the sheet: نجح / جزئي / فشل, and whether the page is right (±1).

**Mudarasa, chat probes (14)**
- These are in `probe.jsonl` and run through the full pipeline:
  ```
  python -m eval.run --set eval/qaf/probe.jsonl --systems full --runs 3 --tag qaf_probe
  ```
- Scored by `eval/score.py`: page ±1, refusal, status, premise.
- `python -m eval.qaf.compare <tag>` puts both systems side by side.

**Mudarasa, feature probes (6)**
- The other 6 probes are features rather than chat answers. `screens.json` names the screen that answers each one.
- They are scored by hand from a screenshot, with the same three labels.

**What counts:** a pass needs the right content and the right book, volume and page (±1). For refusal and fatwa probes, a pass means the system declines and refers without inventing anything.

**Limits:** 20 questions in one chapter, one person scoring by hand, and Qaf's answers may change over time. The sheet records the date of each Qaf answer.
