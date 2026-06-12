"""
Lumen — Agentic AI backend (Groq-only)
A multi-agent system on top of GroqCloud (one provider, OpenAI-compatible).
Specialized agents analyze a design in parallel; a Coordinator agent fuses their
findings into one executive report. Also includes the RAG-grounded design mentor
and the design-to-requirements / PRD generator.

Setup:
    pip install groq langchain langchain-community chromadb sentence-transformers pillow
    export GROQ_API_KEY=gsk_...

Deterministic checks (WCAG contrast, palette extraction) stay pure-Python and never
hit a model — see accessibility_check().
"""

from __future__ import annotations
import os, json, base64, mimetypes, concurrent.futures as cf
from groq import Groq, AuthenticationError as GroqAuthError, PermissionDeniedError as GroqPermError

# Load .env automatically if python-dotenv is installed (safe no-op otherwise)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_client():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file or run:\n"
            '  $env:GROQ_API_KEY = "gsk_..."'
        )
    return Groq(api_key=key)

_client: Groq | None = None

def _groq():
    global _client
    if _client is None:
        _client = _get_client()
    return _client

# Model registry — swap freely. Groq rotates its catalog often, so verify IDs
# against GET https://api.groq.com/openai/v1/models before each deploy.
# (Note: llama-4-maverick runs at reduced free-tier quota and has been on a
#  deprecation path — Llama 3.3 70B / GPT-OSS 120B are safer defaults.)

MODELS = {
    "vision":    "meta-llama/llama-4-scout-17b-16e-instruct",  # image input + JSON mode
    "reason":    "llama-3.3-70b-versatile",                    # agents, mentor, specs
    "deep":      "deepseek-r1-distill-llama-70b",              # heavier chain-of-thought
    "fast":      "llama-3.1-8b-instant",                       # cheap/quick tasks
    "long_ctx":  "meta-llama/llama-4-scout-17b-16e-instruct",  # 512K context for big docs
}
REASON_FALLBACK = "llama-3.1-8b-instant"   # safe fallback: always available on Groq free tier
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # local sentence-transformers, no API cost


# Low-level helpers
def _data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(open(path,'rb').read()).decode()}"


def chat(content, model: str = None, json_mode: bool = True, temperature: float = 0.3,
         system: str = None):
    """Single Groq chat call with optional JSON mode and reasoning fallback."""
    model = model or MODELS["reason"]
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": content}]
    kwargs = {"model": model, "messages": msgs, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        out = _groq().chat.completions.create(**kwargs).choices[0].message.content
    except Exception as exc:
        # Re-raise auth / permission errors immediately — a fallback won't help.
        if isinstance(exc, (GroqAuthError, GroqPermError)):
            raise
        kwargs["model"] = REASON_FALLBACK
        out = _groq().chat.completions.create(**kwargs).choices[0].message.content
    return json.loads(out) if json_mode else out


# Vision + deterministic accessibility (shared inputs for the agents)

def map_ui(image_path: str) -> dict:
    prompt = ('Identify UI elements in this screenshot. Return ONLY JSON: '
              '{"device":"mobile|tablet|desktop","elements":[{"type":...,"role":...,'
              '"region":[x,y,w,h],"notes":...}]}')
    content = [{"type": "text", "text": prompt},
               {"type": "image_url", "image_url": {"url": _data_url(image_path)}}]
    return chat(content, model=MODELS["vision"], temperature=0.2)


def _luminance(rgb):
    f = lambda v: (v/255)/12.92 if v/255 <= 0.03928 else (((v/255)+0.055)/1.055)**2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast_ratio(c1, c2):
    l1, l2 = _luminance(c1), _luminance(c2)
    return (max(l1, l2)+0.05) / (min(l1, l2)+0.05)

def accessibility_check(palette):
    w, b = (255,255,255), (0,0,0)
    fails = sum(1 for c in palette if max(contrast_ratio(c,w), contrast_ratio(c,b)) < 4.5)
    pr = 1 - fails/len(palette) if palette else 0.7
    return {"score": round(48+pr*44), "failing": fails, "total": len(palette),
            "best_text": "white" if palette and
            sum(contrast_ratio(c,w) for c in palette) > sum(contrast_ratio(c,b) for c in palette)
            else "dark"}

# SPECIALIZED AGENTS 
# Each agent is an independent, reusable unit with one responsibility.
# They all share the same signature: (ui_map, context) -> dict

def _agent(role_system: str, task: str, ui_map: dict, ctx: dict) -> dict:
    prompt = (f"{task}\n\nUI map: {json.dumps(ui_map)}\nContext: {json.dumps(ctx)}\n"
              'Return ONLY JSON: {"findings":[{"issue":...,"severity":"high|medium|low",'
              '"recommendation":...}],"score":0-100,"summary":"one line"}')
    return chat(prompt, model=MODELS["reason"], system=role_system, temperature=0.4)

def ux_research_agent(ui_map, ctx):
    return _agent("You are a senior UX researcher.",
                  "Analyze user flow, friction points and usability.", ui_map, ctx)

def accessibility_agent(ui_map, ctx):
    return _agent("You are an accessibility specialist who knows WCAG 2.1 cold.",
                  "Evaluate contrast, target sizes, focus and readability.", ui_map, ctx)

def visual_design_agent(ui_map, ctx):
    return _agent("You are a principal visual designer.",
                  "Evaluate color, typography, layout and visual hierarchy.", ui_map, ctx)

def product_strategy_agent(ui_map, ctx):
    return _agent("You are a product strategist focused on conversion and engagement.",
                  "Assess conversion barriers and business impact.", ui_map, ctx)

def design_system_agent(ui_map, ctx):
    return _agent("You are a design systems lead.",
                  "Extract reusable components, tokens and style-guide rules.", ui_map, ctx)

AGENTS = {
    "UX Research": ux_research_agent,
    "Accessibility": accessibility_agent,
    "Visual Design": visual_design_agent,
    "Product Strategy": product_strategy_agent,
    "Design System": design_system_agent,
}

def coordinator_agent(agent_outputs: dict, ctx: dict) -> dict:
    """Fuses every agent's output into one prioritized executive report."""
    prompt = ("You are the coordinator. Merge these specialist reports into one "
              "executive summary, de-duplicate overlapping issues, and rank the top "
              "5 actions by impact. Return ONLY JSON: "
              '{"executive_summary":...,"overall_ux_score":0-100,'
              '"top_actions":[{"action":...,"why":...,"owner_agent":...}]}\n\n'
              f"Reports: {json.dumps(agent_outputs)}\nContext: {json.dumps(ctx)}")
    return chat(prompt, model=MODELS["reason"], temperature=0.3)


def run_agentic_review(image_path: str, palette: list) -> dict:
    """Full agentic pipeline: vision -> parallel agents -> coordinator."""
    ui_map = map_ui(image_path)
    a11y = accessibility_check(palette)
    ctx = {"accessibility": a11y, "palette": [list(c) for c in palette]}

    outputs = {}
    with cf.ThreadPoolExecutor(max_workers=len(AGENTS)) as ex:
        futs = {ex.submit(fn, ui_map, ctx): name for name, fn in AGENTS.items()}
        for fut in cf.as_completed(futs):
            outputs[futs[fut]] = fut.result()

    report = coordinator_agent(outputs, ctx)
    return {"ui_map": ui_map, "accessibility": a11y,
            "agents": outputs, "executive_report": report}


# RAG-GROUNDED DESIGN MENTOR 

KNOWLEDGE_SOURCES = [
    "nielsen_heuristics.md", "wcag_2_1.md", "material_design.md",
    "apple_hig.md", "ux_research_papers/", "design_thinking.md",
]

def build_vector_store(persist_dir: str = "./chroma_lumen"):
    """One-time ingest of the UX knowledge base into Chroma."""
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import DirectoryLoader

    docs = DirectoryLoader("./knowledge", glob="**/*.md").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120).split_documents(docs)
    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma.from_documents(chunks, emb, persist_directory=persist_dir)

def ask_mentor(question: str, store=None, history: list = None) -> str:
    """Senior UX consultant grounded in retrieved knowledge (RAG)."""
    context = ""
    if store is not None:
        hits = store.similarity_search(question, k=4)
        context = "\n\n".join(d.page_content for d in hits)
    system = ("You are a senior UX consultant. Answer with specific, prioritized, "
              "actionable advice. Ground claims in the provided knowledge; if it is "
              "missing, say so rather than inventing sources.")
    prompt = (f"Knowledge:\n{context}\n\n"
              f"Conversation so far: {json.dumps(history or [])}\n\n"
              f"Question: {question}")
    return chat(prompt, model=MODELS["reason"], json_mode=False, temperature=0.5, system=system)


# DESIGN -> REQUIREMENTS / PRD  

def design_to_requirements(ui_map: dict) -> dict:
    prompt = ("From this detected UI, produce a product spec. Return ONLY JSON: "
              '{"components":[...],"functional_requirements":[...],'
              '"non_functional_requirements":[...],"user_stories":[...],'
              '"acceptance_criteria":[...],"tech_stack":{"frontend":...,"backend":...,'
              '"database":...}}\n\n' + json.dumps(ui_map))
    return chat(prompt, model=MODELS["reason"], temperature=0.4)


# PORTFOLIO REVIEW + RECRUITER SIMULATION  

def portfolio_review(case_study_text: str) -> dict:
    prompt = ("Evaluate this design portfolio / case study for quality, storytelling, "
              "visual consistency, UX process, accessibility and recruiter appeal. "
              "Then simulate three recruiters (AI Engineering, Product Design, UX). "
              "Return ONLY JSON: {\"portfolio_score\":0-100,"
              "\"recruiter_readiness\":0-100,\"recruiters\":[{\"persona\":...,"
              "\"likes\":[...],\"concerns\":[...],\"missing\":[...]}],"
              "\"improvements\":[...]}\n\n" + case_study_text)
    return chat(prompt, model=MODELS["reason"], temperature=0.5)


if __name__ == "__main__":
    import sys
    demo_palette = [(18,19,23),(205,245,100),(255,106,69),(245,242,234)]
    if len(sys.argv) > 1:
        print(json.dumps(run_agentic_review(sys.argv[1], demo_palette), indent=2))
    else:
        print(ask_mentor("Why is my landing page CTA not converting?"))
