# Sources, tools and licences (سجل المصادر والأدوات والتراخيص)

## Books (texts kept on the server only, never in this repository)
| Turath ID | Book | Edition | Page numbering | Role | Rights / terms note |
|---|---|---|---|---|---|
| 1679 | الروض المربع شرح زاد المستقنع، البهوتي (ت ١٠٥١) | دار المؤيد / مؤسسة الرسالة، ط١ ١٤١٧، تخريج عبد القدوس نذير | Printed volume and page (موافق للمطبوع). The e-text was taken from another printing, and the footnotes are missing | Anchor | Text from Turath (Shamela e-text). Rights stay with the publisher |
| 147658 | الروض المربع بشرح زاد المستقنع | دار ركائز، ط١ ١٤٣٨، تحقيق المشيقح والعيدان واليتامى | Printed (3 vols) | Vocalized edition; editors' takhrij and variants | Same |
| 12216 | حاشية الروض المربع، عبد الرحمن بن قاسم (ت ١٣٩٢) | ط١ ١٣٩٧ | Printed (7 vols) | Hashiya | Same |
| 10649 | الشرح الممتع على زاد المستقنع، ابن عثيمين | دار ابن الجوزي، ط١ ١٤٢٢–١٤٢٨ | Printed (15 vols) | Commentary | Same |

**Where the texts come from**
- Turath (api.turath.io, files.turath.io; run by Nuqayah; texts from al-Maktaba al-Shamila).
- We downloaded each book once, slowly, with no key, on 1–2 Oct 2026.
- Turath publishes no terms of use, and its robots.txt sets no content signals. The team decided on 1 Oct to use it.
- What we do with the texts:
  - The full texts stay on our server.
  - This repository publishes the code and short excerpts only.
  - Every citation links to the page on app.turath.io.

**The specialist hasn't approved any book yet.** Library approval: `prep/books/CATALOG.md` (☐ = pending).

## Other sources
| Source | How it is used | Terms note |
|---|---|---|
| Al-Durar Al-Saniyyah (dorar.net/hadith) | A **link-out only**: «ابحث عنه في الدرر السنية» opens Dorar's own search in the browser | No Dorar data is fetched or stored. Dorar blocks scripted requests (Cloudflare 403 on 5 Oct), and we do not get around that. The organizers' reference package names dorar.net/hadith for checking hadith. *Dorar's API terms page could not be read by script; a team member must read it in a browser and record it here.* |
| The organizers' reference package (المرجعية والحزمة العلمية) | The four content levels, see CONTENT.md | — |

## Models and cloud services (as deployed, 5 Oct 2026)
| Service | Deployment | Use | Where the data is processed |
|---|---|---|---|
| Azure OpenAI **gpt-5-mini** (2025-08-07; retires 9 Feb 2027) | Global Standard, resource in **UAE North**, version pinned ("once the current version expires") | Answers, scope gate, support judge, study tools | Global Standard: Azure may process a request in any region; stored data stays in the resource's geography. In UAE North, chat models are offered only as Global Standard |
| Azure OpenAI **text-embedding-3-small** (1024 dimensions) | **Standard (regional)**, UAE North | Dense search | Inside UAE North |
| Azure AI Speech, neural TTS `ar-SA-HamedNeural`; speech to text `ar-SA` | F0 (free), **UAE North** | Recordings for listening, made offline; recitation | Inside UAE North. The browser gets a 10-minute token; the key stays on the server |
| Gemma 4 E4B (`gemma4:e4b-it-qat`) via Ollama, local | — | Backup that doesn't depend on one vendor, scored in the evaluation | On the machine |
| BGE-M3 via Ollama, local | — | Embeddings backup (local hybrid search: 99% gold page in the top 8, against 95% for the deployed hybrid; eval/RETRIEVAL.md) | On the machine |

**Model choice.**
- gpt-5.4, gpt-5.4-mini and gpt-5-nano had **no quota** on the new subscription. The quota request is pending.
- gpt-5-mini was available (500K TPM), so it serves as both answer model and judge.
- The judge is a separate, strict call. It sees only the question, each sentence, its quote and the quote's surrounding text. The word-for-word quote check doesn't depend on any model.
- A different judge model would be stronger. That is listed under Limits, and switching models is one line in `.env`.

## Software (direct dependencies)
| Component | Licence |
|---|---|
| FastAPI, Uvicorn, Gunicorn | MIT / BSD-3 / MIT |
| NumPy | BSD-3 |
| openai (Python SDK) | Apache-2.0 |
| requests, python-dotenv | Apache-2.0 / BSD-3 |
| azure-cognitiveservices-speech (offline TTS build) and microsoft-cognitiveservices-speech-sdk (browser, from jsDelivr) | Microsoft Software License / MIT |
| Fonts: Amiri, IBM Plex Sans Arabic (Google Fonts) | SIL Open Font License 1.1 |
| pytest (development) | MIT |
