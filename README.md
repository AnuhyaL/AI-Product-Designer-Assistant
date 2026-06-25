Designed and built an AI-powered platform that analyzes any interface screenshot, wireframe, or mockup and returns UX scores, accessibility audits, design critiques, and actionable improvement recommendations automating a review process that normally takes designers hours.
Key contributions:

Architected an agentic AI system of five specialized agents (UX research, accessibility, visual design, product strategy, and design systems) coordinated by an orchestrator agent that fuses their findings into a single executive report.
Implemented a Retrieval-Augmented Generation (RAG) pipeline using LangChain and ChromaDB to ground an AI design-mentor chatbot in Nielsen's heuristics and WCAG guidelines, reducing hallucinated advice.
Standardized all LLM inference on the Groq API behind a swappable model registry (Llama 3.3 70B, Llama 4 Scout), enabling low-latency reasoning and easy model swaps.
Engineered real, in-browser WCAG contrast scoring and dominant-color extraction, plus exportable design tokens (JSON).
Built additional AI features including design-to-requirements/PRD generation and a portfolio reviewer that simulates recruiter feedback across seven hiring lenses.
Delivered a working interactive prototype and a full production architecture spanning 10 AI features (FastAPI, Supabase, PostgreSQL, Clerk).
