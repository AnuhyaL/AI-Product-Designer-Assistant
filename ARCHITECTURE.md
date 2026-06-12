# Lumen — AI Product Designer Assistant · Architecture Blueprint

This is the engineering handoff that pairs with the interactive prototype (`index.html`). The prototype shows *what the product feels like*; this document shows *how the real system is built*. It maps directly to the requested stack: Next.js 15 + FastAPI + PostgreSQL/Supabase + Clerk + multi-model AI + Vercel.

---

## 1. System architecture

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENT  — Next.js 15 (App Router) · TypeScript · Tailwind     │
│  ShadCN UI · Framer Motion · TanStack Query                    │
│  Auth handled by Clerk (Google / GitHub / email)               │
└───────────────┬──────────────────────────────────────────────┘
                │ HTTPS (Clerk JWT in Authorization header)
                ▼
┌──────────────────────────────────────────────────────────────┐
│  API GATEWAY — FastAPI (Python 3.12)                           │
│  • Verifies Clerk JWT       • Rate limiting / quotas           │
│  • Request validation       • Routes to services               │
└───┬──────────┬──────────┬──────────┬──────────┬───────────────┘
    ▼          ▼          ▼          ▼          ▼
 Vision    Accessibility  UX/Heuristic  Critique   DesignSystem   (modular services)
 Service     Service       Service      Service      Service
    │          │              │            │            │
    └──────────┴──────────────┴────────────┴────────────┘
                         ▼
        AI ORCHESTRATOR (Groq model router — OpenAI-compatible API)
        Llama 4 Scout (vision) · gpt-oss-120b (reasoning/critique) · llama-3.1-8b-instant (fast)
                         │
        ┌────────────────┴───────────────┐
        ▼                                  ▼
  PostgreSQL (Supabase)            Supabase Storage
  (Users, Projects, Analyses…)     (uploaded images, report PDFs)
```

**Why this shape:** the FastAPI layer stays thin — auth, validation, persistence, and orchestration. Each *analysis engine* is an independent, reusable module so you can deploy, scale, version, or swap any one of them without touching the others (the modular requirement in the spec).

---

## 2. Database schema (PostgreSQL / Supabase)

```sql
-- Users mirror Clerk; Clerk is the source of truth for auth
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id      TEXT UNIQUE NOT NULL,
  email         TEXT UNIQUE NOT NULL,
  full_name     TEXT,
  plan          TEXT DEFAULT 'starter',   -- starter | pro | team
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE teams (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  owner_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE team_members (
  team_id       UUID REFERENCES teams(id) ON DELETE CASCADE,
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  role          TEXT NOT NULL,            -- owner | editor | viewer
  PRIMARY KEY (team_id, user_id)
);

CREATE TABLE projects (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  team_id       UUID REFERENCES teams(id) ON DELETE SET NULL,
  name          TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE uploads (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    UUID REFERENCES projects(id) ON DELETE CASCADE,
  storage_path  TEXT NOT NULL,            -- Supabase Storage key
  width         INT,
  height        INT,
  device_type   TEXT,                     -- mobile | tablet | desktop
  mime_type     TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE analyses (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upload_id       UUID REFERENCES uploads(id) ON DELETE CASCADE,
  status          TEXT DEFAULT 'pending', -- pending | running | done | failed
  ux_score        INT,
  accessibility_score INT,
  hierarchy_score INT,
  heuristic_scores JSONB,                 -- {"visibility":82,...}
  ui_map          JSONB,                  -- detected elements from Vision AI
  created_at      TIMESTAMPTZ DEFAULT now(),
  completed_at    TIMESTAMPTZ
);

CREATE TABLE recommendations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id   UUID REFERENCES analyses(id) ON DELETE CASCADE,
  severity      TEXT,                     -- high | medium | low
  category      TEXT,                     -- accessibility | hierarchy | ux | content
  issue         TEXT,
  impact        TEXT,
  recommendation TEXT
);

CREATE TABLE design_systems (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id   UUID REFERENCES analyses(id) ON DELETE CASCADE,
  tokens        JSONB,                    -- colors, typography, spacing
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reports (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id   UUID REFERENCES analyses(id) ON DELETE CASCADE,
  format        TEXT,                     -- pdf | csv
  storage_path  TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE comments (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id   UUID REFERENCES analyses(id) ON DELETE CASCADE,
  author_id     UUID REFERENCES users(id),
  body          TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);
```

Enable **Row Level Security** on every table; the standard policy is "a user sees rows they own or rows belonging to a team they're a member of." Supabase RLS + the Clerk JWT (`clerk_id` claim) enforce this at the database layer, not just in app code.

---

## 3. Folder structure (monorepo)

```
lumen/
├── apps/
│   ├── web/                        # Next.js 15 frontend
│   │   ├── app/
│   │   │   ├── (marketing)/        # landing, pricing, faq
│   │   │   ├── (auth)/             # Clerk sign-in/up routes
│   │   │   └── (app)/dashboard/    # dashboard, analyze, reports, team, settings
│   │   ├── components/             # ShadCN + custom (ScoreRing, BentoCard, DropZone)
│   │   ├── lib/                    # api client, hooks, utils
│   │   └── styles/
│   └── api/                        # FastAPI backend
│       ├── main.py
│       ├── routers/                # auth, uploads, analyses, reports, teams
│       ├── services/               # one module per engine (see §5)
│       │   ├── vision.py
│       │   ├── accessibility.py
│       │   ├── heuristics.py
│       │   ├── critique.py
│       │   ├── design_system.py
│       │   ├── recommendations.py
│       │   └── reporting.py
│       ├── ai/                     # model router + provider adapters
│       │   ├── orchestrator.py
│       │   ├── providers/openai.py, gemini.py, anthropic.py
│       │   └── prompts/            # versioned prompt templates
│       ├── models/                 # SQLAlchemy models
│       ├── schemas/                # Pydantic request/response
│       └── core/                   # config, auth (Clerk JWT), db session
├── packages/
│   └── types/                      # shared TS types generated from Pydantic/OpenAPI
└── infra/                          # vercel.json, supabase migrations, env templates
```

---

## 4. API design (REST)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/uploads` | Get a signed Supabase upload URL; create `uploads` row |
| `POST` | `/v1/analyses` | Kick off analysis for an upload → returns `analysis_id`, status `running` |
| `GET`  | `/v1/analyses/{id}` | Poll status + full results (scores, ui_map, recommendations) |
| `GET`  | `/v1/analyses/{id}/design-system` | Extracted tokens (JSON) |
| `POST` | `/v1/analyses/{id}/reports` | Generate PDF/CSV → returns signed download URL |
| `GET`  | `/v1/projects` · `POST /v1/projects` | List / create projects |
| `POST` | `/v1/palette` | Generate industry-tuned palette (`{industry}`) |
| `POST` | `/v1/wireframe` | Generate wireframe structure from a text prompt |
| `POST` | `/v1/journey` | Analyze a user-flow string for friction points |
| `GET/POST` | `/v1/teams`, `/v1/teams/{id}/members` | Workspace + RBAC |

Long-running analysis is **async**: `POST /analyses` enqueues a job (Celery/RQ or Supabase Edge Function) and the client polls `GET /analyses/{id}` (or subscribes via Supabase Realtime) — the prototype's progress steps mirror this exact flow.

---

## 5. AI workflow (the orchestrator)

All AI runs through a **single provider — GroqCloud** — via its OpenAI-compatible
endpoint (`https://api.groq.com/openai/v1`). The orchestrator routes each task to
the most appropriate Groq-hosted model. See `groq_orchestrator.py` for runnable code.

```
1. VISION SERVICE
   → Groq: meta-llama/llama-4-scout-17b-16e-instruct  (image input + JSON mode)
   → Prompt returns STRICT JSON: detected elements + bounding regions
     {"elements":[{"type":"button","role":"primary_cta","region":[...]}, ...]}

2. ACCESSIBILITY SERVICE   (deterministic, no LLM)
   → Pixel sampling → dominant colors → WCAG relative-luminance contrast math
   → font-size / touch-target / spacing checks against WCAG 2.1
   → returns score + concrete violations
   (This is the part the prototype already computes for real, in-browser.)

3. HEURISTIC SERVICE
   → Groq: openai/gpt-oss-120b (or llama-3.3-70b-versatile) scores the ui_map
     against Nielsen's 10 heuristics → 0–100 + rationale per heuristic (JSON mode)

4. CRITIQUE SERVICE
   → Groq: openai/gpt-oss-120b — structured professional critique
   → returns issue → impact → recommendation triples with severity (JSON mode)

5. DESIGN SYSTEM SERVICE  (deterministic + LLM)
   → quantize palette, infer type scale & 8px spacing → emit design tokens

6. RECOMMENDATION ENGINE
   → merges + de-duplicates outputs, ranks by severity × impact

7. REPORTING ENGINE
   → renders PDF (WeasyPrint / Playwright) and CSV from the assembled result
```

**Model routing (Groq-only):**

| Task | Groq model ID | Why |
|------|---------------|-----|
| Vision / UI mapping | `meta-llama/llama-4-scout-17b-16e-instruct` | Only Groq tier with image input; supports JSON mode + tool use |
| Heuristics & critique | `openai/gpt-oss-120b` *(fallback: `llama-3.3-70b-versatile`)* | Strongest reasoning model on Groq |
| Cheap/fast tasks (palette labels, journey parsing) | `llama-3.1-8b-instant` | Lowest latency & cost |

Anything purely numerical (contrast, sizing, token extraction) stays deterministic
in Python — free, fast, 100% reproducible, no model call. Every prompt lives in
`ai/prompts/` and is **versioned**.

> ⚠️ **Pin model IDs in config.** Groq rotates preview/hosted models frequently
> (e.g. Llama 4 Maverick was deprecated in Feb 2026). Read the current list from
> `GET https://api.groq.com/openai/v1/models` at startup and fail loudly if a
> pinned ID is missing, rather than discovering it in production.

**Optional resilience:** because Groq is OpenAI-compatible, you can keep the
provider adapter interface generic — a single `LLM_BASE_URL` / `LLM_API_KEY` pair
means you could point the *same* code at OpenAI, Together, or a self-host later
with zero call-site changes. Groq-only is the default; multi-provider stays a
config switch, not a rewrite.

**Cost & reliability controls:** cache vision results per image hash; cap tokens; fail soft (a degraded score beats a 500); log model + prompt version on every `analyses` row for auditability.

---

## 6. Deployment

| Layer | Platform | Notes |
|-------|----------|-------|
| Frontend | **Vercel** | Next.js 15, edge-rendered marketing pages, ISR for dashboards |
| Backend  | **Render / Fly.io / Railway** | FastAPI in a container (Vercel isn't ideal for long-running Python jobs) |
| Worker   | same host | Celery/RQ for async analysis jobs |
| Database | **Supabase** | Postgres + RLS + Realtime + Storage, all in one |
| Auth     | **Clerk** | webhook → `users` table sync on sign-up |
| Secrets  | Vercel + host env | Groq API key server-side only, never exposed to client |

**Env vars:** `GROQ_API_KEY`, `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`. *(Optional generic override: `LLM_BASE_URL` defaulting to `https://api.groq.com/openai/v1`.)*

---

## 7. Suggested build order

1. **Prototype** (done — `index.html`) to lock UX and demo to stakeholders.
2. Clerk auth + Supabase schema + the **Accessibility service** (no AI cost, pure logic — fastest real win).
3. Upload → Vision service → results page wired end-to-end for one screenshot.
4. Add Heuristic + Critique services via the orchestrator.
5. Reporting (PDF/CSV) and design-token export.
6. Team workspace, RBAC, comments.
7. Palette/typography/wireframe/journey generators.

Ship a thin vertical slice end-to-end before going wide — one screenshot all the way through beats ten half-built engines.

---

# Part II — Advanced AI & Agentic Architecture

This turns Lumen from a UX audit tool into an AI design *intelligence* platform: a multi-agent system, RAG-grounded reasoning, a design mentor, and design-to-spec generation. All LLM reasoning runs on **Groq** (`groq_orchestrator.py` is the runnable reference).

## 8. Model registry (Groq)

Everything routes through one swappable map so models can be changed in one place. Groq's catalog churns often — verify IDs at `GET /openai/v1/models` and check the deprecation page before standardizing.

| Role | Model ID | Notes |
|------|----------|-------|
| Vision / UI mapping, long context | `meta-llama/llama-4-scout-17b-16e-instruct` | image input, JSON mode, 512K context |
| General reasoning (agents, mentor, specs) | `llama-3.3-70b-versatile` | best all-round default on Groq |
| Heavy chain-of-thought | `deepseek-r1-distill-llama-70b` | reasoning/math; temp 0.5–0.7 |
| Fast/cheap tasks | `llama-3.1-8b-instant` | lowest latency & cost |
| Reasoning fallback | `openai/gpt-oss-120b` | strong open-weight reasoner |

> The spec named **Llama 4 Maverick** — it works (`meta-llama/llama-4-maverick-17b-128e-instruct`) but runs at half the free-tier quota and has been on a deprecation path, so it's a poor default. Qwen3 32B is also available if you want an alternative reasoner.

## 9. Multi-agent system (Feature 7)

```
Screenshot ─▶ Vision (Llama 4 Scout) ─▶ UI map + deterministic a11y
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼          ▼          ▼          ▼          ▼
        UX Research  Accessibility  Visual    Product    Design System   (run in PARALLEL)
          Agent        Agent       Design     Strategy     Agent
              └───────────────────────────┼───────────────────────────┘
                                          ▼
                              Coordinator Agent (fuse, de-dupe, rank top 5)
                                          ▼
                                  Unified executive report
```

Each agent is an independent unit with one responsibility and an identical `(ui_map, ctx) -> {findings, score, summary}` contract, so agents can be added, removed, or re-ordered without touching the others. They fan out concurrently (`ThreadPoolExecutor`) — Groq's low latency makes the parallel call cheap. The Coordinator is itself an LLM call that receives every agent's JSON and returns one ranked action list. This is implemented in `run_agentic_review()`.

## 10. RAG-grounded knowledge (Features 3 & 4)

```
Question ─▶ embed (MiniLM, local) ─▶ vector search (Chroma) ─▶ top-k chunks
        ─▶ Groq LLM with retrieved context ─▶ evidence-grounded answer
```

- **Stores:** ChromaDB (local/self-host) or Pinecone (managed) via LangChain.
- **Corpus:** Nielsen heuristics, WCAG 2.1, Material Design, Apple HIG, UX papers, design-thinking and accessibility references — ingested once with `build_vector_store()`.
- **Why:** answers cite retrieved guidance instead of hallucinating. Embeddings run locally (sentence-transformers) so retrieval adds no API cost; only the final synthesis hits Groq. The mentor (`ask_mentor()`) is a senior-UX-consultant system prompt over the retrieved context.

## 11. The ten features → where each lives

| # | Feature | Backend function | In the prototype |
|---|---------|------------------|------------------|
| 1 | UX Reviewer | `accessibility_check` + agents | scores + Critique tab |
| 2 | Design → Requirements | `design_to_requirements` | **Build spec** tab |
| 3 | Design Mentor chatbot | `ask_mentor` | **AI Mentor** pane |
| 4 | RAG knowledge base | `build_vector_store` / `ask_mentor` | (grounds the mentor) |
| 5 | Design System generator | `design_system_agent` | Color / Tokens tabs |
| 6 | Redesign generator | coordinator + agents | **Redesign** tab |
| 7 | Multi-agent system | `run_agentic_review` | **Agents** tab |
| 8 | Product spec / PRD | `design_to_requirements` | Build spec tab |
| 9 | Portfolio review | `portfolio_review` | **Portfolio Lab** pane |
| 10 | Recruiter simulation | `portfolio_review` (personas) | Portfolio Lab pane |

## 12. New tables for the agentic layer

```sql
CREATE TABLE agent_runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  agent_name  TEXT,            -- ux_research | accessibility | ...
  model_id    TEXT,            -- which Groq model produced it
  output      JSONB,           -- findings + score
  latency_ms  INT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE mentor_messages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  role        TEXT,            -- user | assistant
  content     TEXT,
  sources     JSONB,           -- retrieved chunk references (RAG provenance)
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE knowledge_documents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source      TEXT,            -- nielsen | wcag | material | hig | ...
  title       TEXT,
  embedded    BOOLEAN DEFAULT false
);
```

(Vector embeddings live in Chroma/Pinecone, not Postgres; `knowledge_documents` just tracks ingest status.)

## 13. Cost, latency & safety notes

- **Latency budget:** vision (~1 call) + 5 parallel agents + 1 coordinator ≈ 3 sequential hops. On Groq that is typically a few seconds end-to-end; without parallelism it would be 7+.
- **Cost control:** cache vision + agent outputs by image hash; embeddings are local; only synthesis calls bill.
- **Reproducibility:** log `model_id` + prompt version on every `agent_runs` row.
- **Graceful degradation:** the deterministic accessibility check always returns a score even if every LLM call fails, so the product never shows a blank result.
