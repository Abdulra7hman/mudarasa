# Research: Qaf (qaf.ai), the named alternative (2 Oct 2026)

Qaf is the system the plan compares against on 20 questions. This is what is public about it.
Everything below is quoted or paraphrased from Qaf's own site (help centre, about page, privacy policy text inside its web app) unless marked as inference.

## Who
- Founders: Abdellatif (co-founded Tarteel AI, head of engineering at Quran.com), Ahmed (built Usul AI; co-founded **Agentset**, an AI-infrastructure startup for RAG), Youssef (designer).
- Product: web app, iOS and Android; 14 languages; subscription with a trial.

## Model (what they say)
- Privacy policy, "Third-Party Subprocessors": AI model providers are used "to generate responses, transcribe audio you submit, and produce embeddings for search … We currently use **Azure OpenAI Service** (Microsoft) as our primary AI subprocessor."
- "Qaf does not train its own foundation models."
- The exact model (e.g. which GPT version) is **not disclosed**.

## Architecture (what they say)
- Retrieval-augmented generation over the **whole Shamela corpus** (~8,500 books, 7.5M pages, 3,100+ authors).
- "The Shamela data is generously provided by the developers behind Turath.io." Their citations link to `app.turath.io/book/<id>` with volume and page, the same source and link format we use.
- A separate "search and retrieval provider" indexes, ranks and retrieves passages (not named).
- Citations open the book, author and exact passage; the user can keep reading, translate or share.
- Disclaimer in the app: "Qaf is a research tool. For fatwas, consult a scholar."

## Inference (not confirmed by Qaf)
- Embeddings and generation both come from Azure OpenAI, so their pipeline is a typical hybrid RAG: chunked pages → OpenAI embeddings + a hosted search index → GPT answer with citations.
- A co-founder's company, Agentset, is an open-source (MIT) RAG platform (ingestion, chunking, hybrid search, agentic "deep research", citations). A public repo by an Ahmed Riad (`ahmedriad1/indexing`, for the Ansari project) uploads Islamic texts to Agentset. That suggests, but does not prove, that Qaf's retrieval runs on Agentset.

## What this means for Mudarasa (our edge, to test, not assume)
| Qaf | Mudarasa |
|---|---|
| Whole Shamela, any madhhab, broad questions | One anchor book and its approved library; refuses outside it |
| Cites pages | Cites pages **and** checks each quote exists in the passage and supports the sentence; drops unsupported sentences |
| No evidence-status label mentioned on its public pages (not yet tested in the app) | Evidence status on every answer (supported / partly / differing / not found) |
| Chat | Aligned study view: matn beside every commentary note and both editions |
| Proprietary, closed models | Open pipeline, reproducible `make eval` |

Same data source (Turath) means a fair head-to-head: differences come from the method, not the texts.

## Sources
- https://help.qaf.ai/ and https://help.qaf.ai/general/what-is-qaf
- https://qaf.ai/about, https://qaf.ai/privacy (text is rendered by the app's JavaScript; read from the app bundle on 2 Oct 2026)
- https://github.com/agentset-ai/agentset
- https://github.com/ahmedriad1/indexing
