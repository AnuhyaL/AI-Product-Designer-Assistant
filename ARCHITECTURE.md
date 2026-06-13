# 🏗️ Lumen – AI Product Designer Assistant

## Architecture Documentation

This document provides a high-level overview of the architecture behind **Lumen**, an AI-powered Product Designer Assistant. It explains how the system is structured, how different components communicate, and how AI services are orchestrated to deliver intelligent design analysis and recommendations.

> **Target Stack**
>
> * Next.js 15
> * FastAPI (Python 3.12)
> * PostgreSQL (Supabase)
> * Clerk Authentication
> * Groq AI Models

---

# 📌 System Overview

Lumen follows a **modular service-oriented architecture**, where each analysis engine operates independently and communicates through a centralized AI orchestration layer.

```
                ┌───────────────────────────────┐
                │         Frontend              │
                │   Next.js 15 + TypeScript     │
                │  Tailwind + ShadCN + Motion   │
                └───────────────┬───────────────┘
                                │
                     HTTPS + Clerk JWT
                                │
                                ▼
                ┌───────────────────────────────┐
                │      FastAPI Backend          │
                │ Authentication & Validation   │
                │ Request Routing & APIs        │
                └───────────────┬───────────────┘
                                │
                ┌───────────────┴───────────────┐
                │        AI Orchestrator         │
                └───────────────┬───────────────┘
                                │
      ┌──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼
 Vision Engine   UX Review    Accessibility   Design System
                                   │
                                   ▼
                        Recommendation Engine
                                   │
                                   ▼
                    PostgreSQL + Supabase Storage
```

---

# 🧩 Architecture Philosophy

The system is designed around **loosely coupled modules**.

Each AI service is responsible for a single task and can be independently:

* Updated
* Scaled
* Replaced
* Tested
* Deployed

This architecture makes the platform easier to maintain while supporting future AI model upgrades.

---

# 🗄️ Database Design

The backend uses **PostgreSQL (Supabase)** as the primary datastore.

Core entities include:

* Users
* Teams
* Projects
* Uploads
* Analyses
* Recommendations
* Design Systems
* Reports
* Comments

Authentication is managed by **Clerk**, while user records are synchronized into PostgreSQL.

## Security

Every table uses **Row Level Security (RLS)**.

Access policies ensure users can only access:

* Their own data
* Shared team resources
* Authorized project information

---

# 📁 Project Structure

```
lumen/

├── apps/
│
├── web/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── styles/
│
├── api/
│   ├── routers/
│   ├── services/
│   ├── ai/
│   ├── models/
│   ├── schemas/
│   └── core/
│
├── packages/
│
└── infra/
```

The backend follows a modular architecture where each AI engine lives in its own service.

---

# 🔌 REST API

| Endpoint                | Description                    |
| ----------------------- | ------------------------------ |
| `POST /v1/uploads`      | Upload design assets           |
| `POST /v1/analyses`     | Start AI analysis              |
| `GET /v1/analyses/{id}` | Retrieve analysis results      |
| `GET /v1/design-system` | Export generated design tokens |
| `POST /v1/reports`      | Generate PDF/CSV reports       |
| `POST /v1/palette`      | Generate AI color palettes     |
| `POST /v1/wireframe`    | Generate wireframes            |
| `POST /v1/journey`      | Analyze user journeys          |
| `GET /v1/projects`      | List projects                  |
| `POST /v1/projects`     | Create project                 |

Long-running operations execute asynchronously through background workers while the frontend polls for status updates.

---

# 🤖 AI Architecture

All AI requests are routed through a centralized **Groq Orchestrator**.

The orchestrator automatically selects the best model depending on the task.

## Processing Pipeline

```
Upload Screenshot
        │
        ▼
Vision Analysis
        │
        ▼
Accessibility Engine
        │
        ▼
UX Heuristic Evaluation
        │
        ▼
AI Product Critique
        │
        ▼
Design System Extraction
        │
        ▼
Recommendation Ranking
        │
        ▼
Report Generation
```

---

# 🧠 AI Services

## Vision Service

* Detects UI components
* Maps layouts
* Identifies buttons, forms, cards, and navigation
* Returns structured JSON

---

## Accessibility Service

Deterministic engine that performs:

* WCAG contrast validation
* Font size checks
* Touch target verification
* Layout spacing analysis

No LLM is required for these calculations.

---

## UX Heuristic Service

Evaluates interfaces using:

* Nielsen's 10 Heuristics
* UX best practices
* Information hierarchy
* Navigation clarity

Returns structured scoring and explanations.

---

## Critique Service

Produces professional design feedback including:

* Issue description
* Business impact
* Severity level
* Actionable recommendations

---

## Design System Service

Automatically extracts:

* Color palettes
* Typography scales
* Spacing tokens
* Component styles

---

## Reporting Service

Generates downloadable:

* PDF Reports
* CSV Exports

---

# 🧠 Multi-Agent AI Workflow

Instead of relying on a single AI response, Lumen uses multiple specialized agents working in parallel.

```
                    Screenshot
                         │
                         ▼
                  Vision Detection
                         │
     ┌──────────┬──────────┬──────────┬──────────┐
     ▼          ▼          ▼          ▼
 UX Agent  Accessibility  Product  Design System
                         Strategy
     │          │          │          │
     └──────────┴──────────┴──────────┘
                    │
                    ▼
            Coordinator Agent
                    │
                    ▼
        Unified Executive Report
```

This approach improves reasoning quality and reduces hallucinations.

---

# 📚 Retrieval-Augmented Generation (RAG)

The AI mentor uses Retrieval-Augmented Generation to answer design questions using trusted references.

Knowledge sources include:

* Nielsen Heuristics
* WCAG 2.1
* Material Design
* Apple Human Interface Guidelines
* UX Research Papers

Embeddings are stored in a vector database and retrieved before generating responses.

---

# 🚀 Deployment Architecture

| Layer           | Technology          |
| --------------- | ------------------- |
| Frontend        | Vercel              |
| Backend         | FastAPI             |
| Database        | Supabase PostgreSQL |
| Storage         | Supabase Storage    |
| Authentication  | Clerk               |
| AI Provider     | Groq                |
| Background Jobs | Celery / RQ         |

---

# 🔐 Security

* Clerk Authentication
* JWT Verification
* Row Level Security
* Secure API Gateway
* Server-side API Keys
* Protected Environment Variables

---

# ⚙️ Environment Variables

```env
GROQ_API_KEY=
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=
```

---

# 🛣️ Development Roadmap

1. Interactive Prototype
2. Authentication & Database
3. Screenshot Upload Pipeline
4. Vision Analysis Engine
5. Accessibility Evaluation
6. UX & Heuristic Analysis
7. AI Critique Generation
8. Design System Extraction
9. Report Generation
10. Team Collaboration & Workspace Features

---

# 📈 Scalability

The architecture is designed to support:

* Independent AI services
* Horizontal scaling
* Future model replacements
* Multi-provider AI routing
* Team collaboration
* Enterprise deployments

This modular foundation allows Lumen to evolve from a UX review tool into a comprehensive AI-powered product design intelligence platform.

