# Lumen — Run & Build Guide (Windows + VS Code)

A step-by-step, beginner-friendly guide to running this project on your own machine. It's staged into levels — **each level works by itself**, so stop whenever you've seen enough. Don't install everything up front.

- **Level 0** — See the prototype (no coding, 2 minutes)
- **Level 1** — Your first *real* Groq AI call (about 20 minutes)
- **Level 2** — Run the full multi-agent review on a screenshot
- **Level 3** — Add the RAG knowledge base (optional, heavier)

---

## Level 0 — See the prototype (no install)

The whole frontend is one file: `index.html`.

1. Find `index.html` in your downloads.
2. Double-click it. It opens in your browser and just works — landing page, dashboard, upload, analysis, Mentor, Portfolio Lab.

That's it. Nothing to install. If you want to *edit* it, open the file in VS Code, change some text, save, and refresh the browser tab.

> To put it online (free): go to **app.netlify.com/drop** and drag `index.html` onto the page. You'll get a public link in seconds.

---

## Level 1 — Your first real Groq AI call

This is where the AI stops being simulated and actually thinks. You'll get a free Groq key, install one Python package, and run the design mentor from your terminal.

### 1a. Install Python
1. Go to **python.org/downloads**, download Python 3.12 (or newer).
2. Run the installer. **On the first screen, tick the box "Add python.exe to PATH"** before clicking Install. (This one checkbox saves a lot of pain.)
3. To confirm it worked, open VS Code → menu **Terminal → New Terminal**, then type:
   ```powershell
   python --version
   ```
   You should see something like `Python 3.12.x`. If it says "not recognized," restart VS Code and try again.

### 1b. Get a free Groq API key
1. Go to **console.groq.com** and sign up (free, no credit card).
2. Open **API Keys** → **Create API Key** → copy it. It looks like `gsk_...`.
3. Keep it private — treat it like a password.

### 1c. Open the project in VS Code
1. VS Code → **File → Open Folder** → pick the folder containing `groq_orchestrator.py`.
2. Open a terminal (**Terminal → New Terminal**).

### 1d. Install the one package you need
```powershell
pip install groq
```
(If `pip` isn't recognized, use `python -m pip install groq` instead.)

### 1e. Set your key for this terminal session
In the **PowerShell** terminal (VS Code's default), paste this with your real key:
```powershell
$env:GROQ_API_KEY = "gsk_your_key_here"
```
> This lasts only for the current terminal window. That's fine for now. (To make it permanent later: Windows search → "Edit environment variables for your account" → New → name `GROQ_API_KEY`, value your key → reopen VS Code.)

### 1f. Run it
```powershell
python groq_orchestrator.py
```
With no file argument, the script asks the mentor *"Why is my landing page CTA not converting?"* and prints a real answer from Groq's Llama 3.3 70B. **If you see a thoughtful paragraph appear, you just ran live AI.** 🎉

---

## Level 2 — Full multi-agent review on a screenshot

Now run the headline feature: five specialist agents + a coordinator analyzing a real image.

1. Put any screenshot (PNG or JPG) in the project folder, e.g. `test.png`.
2. With your key still set in the terminal, run:
   ```powershell
   python groq_orchestrator.py test.png
   ```
3. You'll get a JSON report: the vision model's UI map, each agent's findings, and the coordinator's ranked executive summary.

What's happening: the **vision model** (Llama 4 Scout) reads the image, the **five agents run in parallel**, and the **coordinator** fuses them — exactly the flow drawn in `ARCHITECTURE.md` (Part II, section 9). Still only needs the `groq` package.

---

## Level 3 — Add the RAG knowledge base (optional)

This makes the mentor answer from real UX sources instead of general knowledge. It's heavier (bigger installs, a few minutes), so only do it if you're curious about how RAG works.

1. Install the extras:
   ```powershell
   pip install langchain langchain-community chromadb sentence-transformers
   ```
2. Make a folder named `knowledge` next to the script and drop in some `.md` files (notes on Nielsen's heuristics, WCAG, etc. — even short ones to test).
3. In a Python session or a small script:
   ```python
   from groq_orchestrator import build_vector_store, ask_mentor
   store = build_vector_store()        # reads ./knowledge, builds the vector index
   print(ask_mentor("How do I improve contrast?", store=store))
   ```
   The answer is now grounded in the documents you provided.

---

## Common problems & fixes

| Symptom | Fix |
|--------|-----|
| `'python' is not recognized` | You missed "Add to PATH" during install. Reinstall and tick the box, or restart VS Code. |
| `'pip' is not recognized` | Use `python -m pip install groq` instead. |
| `KeyError: 'GROQ_API_KEY'` | The key isn't set in *this* terminal. Re-run the `$env:GROQ_API_KEY = "..."` line. |
| `groq.AuthenticationError` | The key is wrong or has extra spaces/quotes. Recopy it from the Groq console. |
| `RateLimitError` | Free tier limits hit (about 30 requests/minute). Wait a minute and retry. |
| A model ID error | Groq rotates models. Check **console.groq.com/docs/models** and update the IDs in the `MODELS` map at the top of `groq_orchestrator.py`. |

---

## What the three files are

- **`index.html`** — the entire interactive frontend (the thing recruiters click).
- **`groq_orchestrator.py`** — the real AI backend: multi-agent review, RAG mentor, requirements/portfolio generators.
- **`ARCHITECTURE.md`** — the full system design (schema, API, agent + RAG diagrams, the 10-feature map).

## A realistic mental model

The prototype (`index.html`) and the AI brain (`groq_orchestrator.py`) are currently **two separate things**. Levels 1–3 run the brain on its own in the terminal. *Connecting* them — so clicking "Analyze" in the browser calls the Python code — is the next project after this guide: a small FastAPI server that the page talks to. When you're ready for that, that's the piece to build next.
