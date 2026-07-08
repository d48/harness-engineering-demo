# Harness Engineering — Demos & Slides

A slide deck and five runnable demos teaching the concepts from
**Lilian Weng, ["Harness Engineering for Self-Improvement"](https://lilianweng.github.io/posts/2026-07-04-harness/) (Lil'Log, Jul 2026)** —
what an agent *harness* is, the design patterns behind Claude Code / Codex-style
agents, and how harnesses themselves become the object of optimization on the
road to recursive self-improvement (RSI).

## Quick start

Requires only Python 3.10+ (stdlib only — no packages, no API keys, no network).
`npm install` is not required — `package.json` just wraps the Python entry point
for convenience.

```bash
python3 demo/run.py            # interactive menu
python3 demo/run.py 1          # run one demo
python3 demo/run.py all        # run everything
python3 demo/run.py all --fast # skip the dramatic pauses (smoke test)
```

or, equivalently, via npm:

```bash
npm run demo        # interactive menu
npm run demo:1       # run demo 1 (demo:2 … demo:5 also available)
npm run demo:all     # run everything
npm run demo:all -- --fast   # extra flags go after `--`
```

Open `slides/harness-slides.html` in a browser for the presentation
(arrow keys to navigate, `N` toggles speaker notes, `O` shows an overview grid),
or launch it with:

```bash
npm run slides
```

## The demos

Each demo maps to a section of the article. The "model" in demos 1–3 is a
deterministic script (so the walkthrough is reproducible live on stage), but
**everything around it is real**: real files, real subprocesses, real test
runs, real threads, real accept/reject gates. Demos 4–5 are fully real
optimization loops with no script at all. That asymmetry is the point: the
harness is genuine machinery, and you could swap the scripted model for a
live LLM without touching the rest.

| # | Demo | Article concept | What actually happens |
|---|---|---|---|
| 1 | `demo1_agent_loop.py` | Workflow automation: the agent loop | plan → act → observe → improve until a *real* failing test goes green; the harness re-verifies the claim itself |
| 2 | `demo2_memory.py` | File system as persistent memory | Same task, 3-message context window: run A loses its findings; run B journals to `NOTES.md`, survives a hard context reset, and finishes |
| 3 | `demo3_subagents.py` | Sub-agents & background jobs | 3 hypotheses investigated by 3 real threads in parallel; results merged through `findings/*.md` files, not chat context |
| 4 | `demo4_self_harness.py` | Self-improving harness (Self-Harness) | Live propose→evaluate→accept loop: weakness mining, bounded edits, held-in/held-out validation — a reward-hack proposal is caught and rejected |
| 5 | `demo5_evolution.py` | Evolutionary search (AlphaEvolve / DGM) | Real code inside `EVOLVE-BLOCK` markers is mutated, executed, and selected until it exactly rediscovers a hidden formula (MSE = 0) |

## Repo layout

```
demo/
  mini_harness/        # the teaching harness: ~200 lines, deliberately simple
    loop.py            # the agent loop + context-window assembly
    tools.py           # real tools: read/write/edit/ls/grep/bash over a sandbox
    model.py           # the scripted "model" (swap for a real LLM here)
    trace.py           # terminal rendering: THOUGHT / TOOL / OBSERVE / verdicts
  demo1..demo5_*.py    # the five demos
  run.py               # menu / runner
slides/
  harness-slides.html  # self-contained deck with diagrams (no dependencies)
scripts/
  open-slides.js       # cross-platform "open the deck in a browser" for `npm run slides`
```

## Presenting this

Suggested flow for a ~30-minute engineering talk:

1. Slides 1–8: what a harness is, the three design patterns (run demos 1–3 as you go).
2. Slides 9–14: the optimization ladder — prompts → context → workflow → harness code (run demos 4–5).
3. Slides 15–19: why full RSI isn't here yet — failure modes and the seven bottlenecks.

Every demo ends with a `TAKEAWAY` block that matches the corresponding slide's
speaker notes, so the deck and the terminal reinforce each other.
