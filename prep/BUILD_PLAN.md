# Mudarasa: build plan for Mon 5 – Tue 6 Oct (Azure models + seven additions)

## Context
- The prep pipeline works (scope check → hybrid search → cited answer → quote check), but answers from the local
  Gemma 4 E4B fall short of the quality you want and take 35–75 s. You want Azure OpenAI.
- **Product, repo, video and deck freeze on 6 Oct at 23:59**, and nothing may change after that. Switching the model on
  judging day would be a code change to the judged product, so the switch happens **now**, by config.
- You also want **all** the additions to work in the judged product, at least as working prototypes, aiming for ~90%:
  audio reading, study tools, memorization, word meaning, takhrij, spaced repetition and notes export.
- The build hasn't started: no repo yet. It's you plus Claude, starting 09:30 Mon, with about 30 working hours.
- Five of the seven criteria (80 points) reward a reproducible evaluation against baselines. So the core and the tests
  come first, and the additions sit behind feature flags with a cut line.

## Decisions (you, 5 Oct)
| Topic | Decision |
|---|---|
| Model | Test for free first, then confirm on Azure, then pick on score, speed and cost. Gemma stays as the scored backup that doesn't depend on one vendor |
| Team | You + Claude. Claude drafts the test set and gold citations from the texts; you review. Disclosed as "model-drafted, reviewed" |
| Hosting | **Azure App Service** (Linux B1, Always On). HTTPS comes built in, which the microphone needs. Zip deploy means the book texts never pass through git |
| Takhrij | Dorar is treated as a library source, but only as a **link-out** (see findings). Gradings shown in the app are quoted word for word from library notes (Rakaiz, Ibn Qasim) and attributed |

## Findings that shape the plan (checked 5 Oct)
1. **Correction to what I told you about gpt-4.1.**
   - Microsoft's retirement table (updated 23 Sep 2026) says gpt-4.1 is *Deprecated*, so new customers can't deploy it. It retires on 2027-04-14.
   - The model that retires on 14 Oct 2026 is gpt-4.1-nano, not gpt-4.1.
   - The models available now, all GA: gpt-5 and gpt-5-mini (until Feb 2027); gpt-5.4 and gpt-5.4-mini (until Sep 2027);
     gpt-5.5; gpt-5.6-luna, -sol and -terra. Embeddings: text-embedding-3-large and -small.
   - GPT-5.x models don't accept `temperature`. We fix `reasoning_effort` instead, run 3 times, and report the mean and range.
2. **No Azure access exists on this machine.** There's no az CLI, no `~/.azure`, no keys in env or any `.env`, and no
   `openai` package. gh is logged in, but its token can't call GitHub Models.
3. **Try before you buy.**
   - **GitHub Models** is free and rate-limited. It has gpt-5, gpt-5-mini and gpt-5.4-mini, and needs a
     fine-grained token with *Models: read*.
   - A **new Azure account** gets $200 of credit for 30 days. That covers the build, the tests and judging, which ends 22 Oct.
     Trial subscriptions get a lower OpenAI quota; upgrading to pay-as-you-go keeps the credit.
   - **Speech F0** is free: 0.5M characters of text to speech and 5 hours of speech to text a month. All the audio fits (~245k characters).
4. **Estimated cost.**
   - gpt-5 + gpt-5-mini: about $0.03 a question. gpt-5-mini alone: about $0.006. The test runs (~900 answers) cost about $27 or $6.
   - The model check measures the real cost per question from logged tokens.
   - App Service B1 is about $13 a month. Set a **$100 budget alert**.
5. **Linking bug in the prep code.**
   - `q3()` in `prep/step2_extraction/analyse.py:205` looks each note up on the page where its unit starts (`pg = u["pg"]`). Units cross pages and note numbers restart each page.
   - So about 97 of the 222 Ibn Qasim notes get another note's text.
   - `linking_sample_50.csv` is affected (about 20 of its 50 rows). Regenerate it before anyone labels it.
6. **The tashkeel comes from Rakaiz.**
   - Rakaiz (147658) has about 0.2 tashkeel marks per letter, against 0.006 for 1679. The Zad matn alone (11230) has none.
   - Audio and memorization therefore use the Rakaiz text: 179 of the 193 deep-chapter units have the same matn in both.
   - The study view gets an edition switch (1679 / Rakaiz).
   - Honorific ligatures (ﷺ ﵀ ﵁) are spelled out before text to speech.
7. **Dorar blocks scripted access.**
   - Cloudflare returns 403 to plain curl, including on its API page (article 389). The main community wrapper shut down in May 2026 for this reason.
   - We don't get around it. Takhrij links out to Dorar's search, and you read its terms in a browser for SOURCES.md.
8. **Al-Misbah al-Munir (Turath 12145) has 2,940 root headings**, so looking a word up by its root works. It needs one fetch and your approval.
9. **The repo would leak book text.** These must stay out of git, not just `books/`:
   - `prep/step2_extraction/results/*.json` and `linking_sample_50.csv`
   - `prep/research_qaf/qaf_probe_questions.csv`
   - `prep/retrieval/cache_embeddings.json`
   - everything under `data/`
10. **The live backup can't be Gemma**, because App Service has no GPU.
    - Live backup chain: main Azure deployment → second deployment → search-only mode (cited passages, no generated answer).
    - Gemma is scored offline as the backup that doesn't depend on one vendor.

## Architecture
FastAPI plus plain HTML/JS (one process, no build step). The repo is a new folder, `~/Desktop/MUDARASA/mudarasa/`; the texts go in the gitignored `data/`.

```
mudarasa/  STARTING_POINT.md README.md(AR+EN) SOURCES.md CONTENT.md Makefile requirements.txt .env.example .gitignore
  app/      config textnorm books segment link ingest retrieval llm prompts verify pipeline
            study_tools glossary takhrij matn recite main(FastAPI)
  web/      index.html css/ js/{api,router,study,chat,listen,recite,tools,word,srs,notebook,settings}.js fonts/
  scripts/  fetch_books build_index build_tts build_tools model_check deploy
  eval/     testset.jsonl run score judge report retrieval_check additions_check qaf/ linking/ recite/ results/ REPORT.md ERRORS.md
  tests/    test_normalise test_linking(page-bug regression) test_quotes test_recite test_status
  prep/     the starting point (code and reports, texts excluded)   data/ (gitignored) books/ build/ audio/ tools/ logs/
```

| New module | Reused from prep | Change |
|---|---|---|
| `app/textnorm.py` | `analyse.normalise`, `TASHKEEL`, `AR_DIGITS`, `FN_SEP`, `MARK`, `strip_markup`, `split_notes` | + `join_continuations()` (Rakaiz «=» footnotes that carry over a page); + `speakable()` for TTS |
| `app/books.py` | `analyse.load_pages` | Reads `data/books/<id>/full.json` by page range; `chapter_range()` from the headings and `page_map` |
| `app/segment.py`, `app/link.py` | `analyse.units`, `locate`, `word_cover`, `q3`, `q4`, `q5`, `ref` | Units keep a map from text position to page, so each `(n)` marker resolves to its real page (**bug fix**). The Mumti' sections and the Rakaiz vocalized matn and footnotes are attached to each unit |
| `app/retrieval.py` | `retrieval.stem`, `tokens`, `BM25`, `Retriever`, `RRF_K`, `toc_passages`, `TAKHRIJ` | `embed()` uses Azure `text-embedding-3-large`, with local BGE-M3 as backup and keyword-only search if both fail. Passages linked to the open paragraph go first |
| `app/llm.py` | `run_check.ask` | Providers `azure` / `github` (free test) / `ollama`. Strict JSON schema, `reasoning_effort`, retries. Returns tokens, latency and cost |
| `app/prompts.py` | `RULES_V2`, `SCHEMA_V2`, `CLOSED_FAIR`, `SCOPE_RULES`, `EXTRA_RULES` | + `strict()` schema converter; the judge prompt; the study-tool prompt |
| `app/pipeline.py`, `app/verify.py` | `server.answer`, `REFUSALS`, `STATUS_AR`, `PMARK`, the quote-check loop | + support judge (mini model). Retrieval and verification can be switched off for the comparison runs. Personal-fatwa and false-premise wording comes from `answer_policy.md` |
| `web/` | `demo/index.html` (RTL, dark mode, tashkeel and font toggles, `highlight()`) | Split into modules with a hash router |
| `eval/score.py`, `scripts/model_check.py` | `score_all`, `page_hit`, `summarise`, `retrieval_test.hit`, `run_variants.main` | Test-set format, 3 runs, cost |

## The additions: minimal designs (each behind a flag, labelled «تجريبي»)

**Audio reading**
- **Offline:** `build_tts.py` with the Azure Speech SDK, voice `ar-SA-HamedNeural`.
  - It reads the Rakaiz paragraphs, Ibn Qasim notes, Mumti' sections and matn lines. Text goes through `speakable()` first.
  - The MP3s and word timings are saved; each word is matched to the source text by searching forward.
- **API:** `/api/audio/{chapter}`.
- **Screen:**
  - A player: play/pause, ±10 s, speed.
  - Modes: «المتن والشرح» / «مع حواشي ابن قاسم» / «المتن فقط».
  - The current word is highlighted and the page scrolls with it. Tapping a note plays it, then goes back to where you were.
- **Backup:** estimated timings, or the browser's own voice with paragraph highlighting only.
- **Cost:** $0 on F0.

**Study tools**
- **Offline:**
  - About 15 sections. Each gets a summary, quiz questions and flashcards, every item with a passage and a quote.
  - Then the quote check and the judge. Anything that fails is dropped, and the counts are logged.
- **API:** `/api/tools/{section}`, plus generate on demand (cached and rate-limited).
- **Screen:** cited summary; quiz that reveals the quote and page; flip cards with «أضف إلى المراجعة» and «أضف إلى دفتري».

**Memorization**
- **Matn:** `matn.py` takes the 1679 matn, splits it into lines of 6–14 words, and gives each word the Rakaiz vocalization.
- **Hiding:** all words / first letters / every other word.
- **Microphone:**
  - The Azure Speech JS SDK runs from a pinned CDN link, with `ar-SA`, continuous recognition and the line's words as a phrase list.
  - The token comes from `/api/speech/token` (10 minutes, rate-limited); the key never leaves the server.
- **Feedback:**
  - Partial results reveal words in green.
  - Final results flag mistakes: red for a wrong word, orange for a skipped one.
  - At the end: a score and «أضف الأخطاء إلى المراجعة».
- **Matching:** normalise and stem each word; a word matches when it is equal or at least 75% similar; look up to 3 words ahead to catch a skip. The same code in `app/recite.py` is used for the eval.
- **Backups:** Chrome's built-in speech recognition, then typed recitation (also for judges without a microphone).

**Word meaning**
- **Offline, a glossary from:**
  - Ibn Qasim notes, keyed by the words just before the marker. They mostly gloss that word.
  - «أي…», «لغة…» and «بفتح/بكسر…» glosses in all four books.
  - The Misbah root headings.
- **API:** `/api/word?w=&unit=` returns cited definitions in this order: notes on this unit → gloss in the same unit → chapter glossary → Misbah root.
- **Screen:** a popover. «اشرح من النصوص» sends a checked question through `/api/ask`.

**Takhrij**
- Rakaiz and Ibn Qasim notes are sorted into takhrij, manuscript variants and other.
- Grading phrases (صححه، حسنه، جوّد إسناده، ضعيف…) are pulled out with who gave them, and attached to the right unit.
- **Screen:**
  - The note shown word for word, grading highlighted and attributed.
  - «لم يذكر المصدر حكمًا» when the note has none.
  - An «ابحث في الدرر السنية» link-out. There are about 34 takhrij notes in the deep chapters, 21 with a grading.

**Spaced repetition**
- SM-2 scheduling in localStorage. Cards come from study tools, memorization mistakes and saved answers.
- A «مراجعة اليوم (n)» screen; JSON export and import; a notice that the data stays in this browser.

**Notes export**
- A notebook in localStorage. «أضف إلى دفتري» works on answers, summaries, cards, word meanings and takhrij.
- Exports as Markdown with every citation written out (book, volume, page, Turath link, quote).
- An RTL print view gives a PDF.

**Bare minimum for each addition if time runs short:**
- Takhrij: notes plus the link-out.
- Word meaning: Ibn Qasim notes only.
- Study tools: باب المياه only.
- Audio: paragraph highlighting only.
- Memorization: typed recitation plus Chrome's speech recognition.
- Spaced repetition: 3 Leitner boxes.
- Export: `.md` only.

## Schedule (C = Claude, BG = background job)
**Mon 5 Oct**

| Time | You | Claude |
|---|---|---|
| 09:30–10:15 | Empty public GitHub repo. Azure free account. One Azure OpenAI (Foundry) resource in a region with the GPT-5.4 models (e.g. Sweden Central / East US 2): deploy gpt-5.4, gpt-5.4-mini and text-embedding-3-large, all `NoAutoUpgrade`. Speech F0 in the same region. $100 budget alert. GitHub fine-grained token with *Models: read*. All keys go into `.env` | Repo, `.gitignore` (finding 9), `STARTING_POINT.md` (prep 1–3 Oct; Qaf sheet edited 4 Oct; no product code before 5 Oct; history starts 5 Oct, nothing backdated), copy of prep without texts, tag `start` |
| 10:15–11:00 | Read the free-test table | `llm.py`; free test on GitHub Models: the 10-question check on gpt-5-mini, gpt-5.4-mini and gpt-5 where the free limits allow |
| 11:00–13:00 | Approve the library (5 books incl. 12145) in `library/approved.json` | Ingest the 3 deep chapters, with the page-bug fix and tests that reproduce the prep numbers; regenerate the linking sheet; fetch 12145. Azure model check (≈$1): gpt-5.4 (effort none/low), gpt-5.4-mini, and gpt-5.5/5.6 if quota allows → **pick the answer model and the judge model** |
| 13:00–15:00 | Review the test set as it's drafted | Retrieval with Azure embeddings (re-run `retrieval_test`), pipeline with the judge, FastAPI routes, `make eval-quick`. 100-item test set drafted with gold pages taken from the source passages |
| 15:00–17:00 | Try the UI as it lands; confirm testers | Study view (edition switch, commentary side panel), chat with evidence badges, report button, settings, 3 suggested questions, AI disclosure, phone layout |
| 17:00–18:00 | Phone test over HTTPS | App Service zip deploy, Always On, `/healthz`, rate limit, answer cache, search-only backup; `make eval RUNS=1` |
| **18:00 cut line** | **The full test set runs end to end on the live URL. If not, no additions until it does** | |
| 18:00–22:00 | User sessions if booked (task cards, Arabic SUS); otherwise review the test set and enter Qaf rows | BG: 3 runs each of full and no-retrieval; a TTS probe on 2 clips, then the full batch. C: takhrij → word meaning → study tools (generated in BG) → notes export |
| Overnight | — | BG on the laptop: Gemma backup, 3 runs; the rest of the TTS |

**Tue 6 Oct**

| Time | You | Claude |
|---|---|---|
| 08:00–10:30 | Read REPORT v1; before and after screenshots | `ERRORS.md`; the top 3 fixes from users and eval |
| 10:30–12:00 | Qaf, 20 questions with screenshots; record 12 recitation clips (`arecord -r 16000 -c 1`) | Listen mode |
| 12:00–14:45 | Deck skeleton | Memorization; spaced repetition with export/import |
| 14:45–15:30 | — | `additions_check.py`; BG: final eval runs on the final code |
| **15:30 additions cut line** | **Anything not working on the demo path gets its flag switched off and moves to the Next slide** | |
| 15:30–17:30 | README (AR/EN), SOURCES.md (incl. Dorar terms), CONTENT.md | Accessibility pass, scan for texts and secrets, final deploy |
| **18:00 freeze** | Tag `v1.0-submission` | Check every number in the deck against REPORT.md |
| 18:00–21:00 | Video (2:00 max), deck, clean-browser test, **submit by 21:00** | — |

After each milestone: `python3 prep/conversation/export_conversation.py` and a memory update.

## Evaluation (`make eval`; every system 3 runs, mean and range, `meta.json` with commit, deployments and prices)
| System | How it runs |
|---|---|
| Full | Scope gate → hybrid search → answer model → quote check → judge |
| No verification | The same answers as Full, scored before checking. Costs nothing extra |
| No retrieval | `CLOSED_FAIR` prompt on the same model |
| Backup | The whole pipeline on Gemma via Ollama, run overnight |
| Qaf | 20 questions entered by hand, with screenshots → `eval/qaf/` |
| Retrieval only | keyword / BGE-M3 / text-embedding-3-large / hybrid: is a gold page in the top 8? |

**What gets scored**
- Citation accuracy (page ±1), correct refusals and false refusals, referrals, premises caught, evidence-status match.
- Every critical item must pass.
- Share of sentences that survive checking, judge drop rate, correctness 0–2, latency, cost per question.
- Judge fixtures: the step-3 Q02 and Q08 drift («يكره» to «لا يجوز») must be rejected.

**Small checks for the additions** (labelled "small checks")
- Study tools: % of items with a verified quote and judge support, plus 20 audited by hand.
- Word meaning: 40 words, 20 of them with an Ibn Qasim gloss as the gold answer.
- Takhrij: % of hadith notes attached, % with a grading, 10 checked by hand, and every grading shown copied word for word.
- Audio: coverage, % of words with timings, and mispronunciations in 5 clips.
- Memorization: 12 clips, 6 with a planted mistake; word accuracy and mistake detection.
- Spaced repetition and export: a `node --test` round trip.
- Linking: precision on the regenerated sample.

## Risks
| Risk | Mitigation |
|---|---|
| Not enough time | Cut lines at 18:00 Mon, 15:30 Tue and 18:00 Tue; feature flags |
| Azure onboarding or quota slow | Start at 09:30; build on Ollama/GitHub Models until the keys work; upgrade to pay-as-you-go if quota is too small |
| Credit runs out during judging | Budget alert; daily cap on requests; cached answers to the suggested questions |
| Judge too strict, causing false refusals | Watch the drop rate in run 1; tune using the Q02/Q08 fixtures |
| Arabic word timings or speech recognition fail | 2-clip probe first; estimated timings; typed recitation |
| Book texts leak into the public repo | Gitignore (finding 9) plus a scan for long Arabic passages and keys before each push |
| Demo breaks during judging, 7–22 Oct | `NoAutoUpgrade`, Always On, uptime alert, search-only mode |
| Privacy | No IP addresses or identifiers in logs; recitation audio goes to Azure and is not stored by us. Say so in the app |

## Verification
- `pytest tests/` passes, including a linking regression showing the page bug fixed: the note text matches the marker's own page.
- `make eval-quick`: the 14 prep questions, all answered or refused correctly.
- `make eval RUNS=3` → `eval/REPORT.md` with every system above. `eval/retrieval_check.py` and `eval/additions_check.py` produce their tables.
- Live, on a phone, on the App Service HTTPS URL:
  - the 3 suggested questions, and open a citation's page
  - play audio with the word highlighted
  - recite a line with the microphone
  - tap a word for its meaning, and open a takhrij
  - add items to the notebook and export `.md`
  - review today's cards
- `git ls-files` scan: no `.env`, no book text, no `data/`.
