"""Demo 2 — Pattern 2: File system as persistent memory.

Article section: "Harness Design Patterns > File system as persistent memory"

A multi-step audit task must survive a context window that only holds the
last 3 exchanges, plus a hard "context reset" (fresh session) halfway
through. Run A keeps state only in context — the early findings literally
fall out of the window. Run B journals every finding to NOTES.md and
recovers the full state after the reset by reading the file.
"""

import tempfile
from pathlib import Path

from mini_harness import Action, AgentLoop, ScriptedModel, Toolbox, Trace
from mini_harness.trace import GREEN, RED

SERVICES = {
    "services/auth.cfg": "timeout=30\nretries=3\ntls=on\n",
    "services/billing.cfg": "timeout=120\nretries=0\ntls=off\n",
    "services/search.cfg": "timeout=15\nretries=2\ntls=on\n",
}

TASK = "Audit every service config for tls=off and report all offenders."


def seed_workspace(toolbox: Toolbox) -> None:
    for path, content in SERVICES.items():
        toolbox.write(path, content)


def run_without_memory() -> None:
    trace = Trace(agent="amnesiac", color=RED)
    trace.section("RUN A — context-only state (window keeps last 3 exchanges)")
    script = [
        Action(thought="Check auth.cfg first.", tool="read", args={"path": "services/auth.cfg"}),
        Action(thought="auth is fine (tls=on). Next: billing.", tool="read", args={"path": "services/billing.cfg"}),
        Action(thought="billing has tls=off — offender #1. I'll keep that in mind. Next: search.",
               tool="read", args={"path": "services/search.cfg"}),
        Action(thought="search is fine. Now, which services were offenders again...?",
               tool="ls", args={"path": "services"}),
        Action(
            thought="My earlier observations scrolled out of the context window. "
                    "I only remember the recent files — I cannot reconstruct the list.",
            final="INCOMPLETE: findings were lost when they left the context window.",
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="harness_demo2a_") as ws:
        toolbox = Toolbox(Path(ws))
        seed_workspace(toolbox)
        loop = AgentLoop(ScriptedModel(script), toolbox, trace, context_limit=3)
        result = loop.run(TASK)
        window = loop._assemble_context(result.history)
        trace.note("What the model could still see at the end (its whole world):")
        for line in window:
            flat = " / ".join(part.strip() for part in line.splitlines() if part.strip())
            trace.note(f"  | {flat[:90]}")
        trace.verdict(False, "the billing.cfg finding is gone — it left the window")


def run_with_memory() -> None:
    trace = Trace(agent="journaler", color=GREEN)
    trace.section("RUN B — same window, but findings journaled to NOTES.md")

    session1 = [
        Action(thought="Before anything: create a durable notes file. Context is ephemeral; disk is not.",
               tool="write", args={"path": "NOTES.md", "content": "# Audit progress\n\nTODO: auth, billing, search\n"}),
        Action(thought="Check auth.cfg.", tool="read", args={"path": "services/auth.cfg"}),
        Action(thought="auth clean. Record it — my context will not remember this for long.",
               tool="edit", args={"path": "NOTES.md", "old": "TODO: auth, billing, search",
                                  "new": "- auth: OK (tls=on)\nTODO: billing, search"}),
        Action(thought="Check billing.cfg.", tool="read", args={"path": "services/billing.cfg"}),
        Action(thought="billing has tls=off — offender. Journal it immediately.",
               tool="edit", args={"path": "NOTES.md", "old": "TODO: billing, search",
                                  "new": "- billing: OFFENDER (tls=off)\nTODO: search"}),
    ]

    session2 = [
        Action(thought="Fresh session, empty context. First move: read my own notes.",
               tool="read", args={"path": "NOTES.md"}),
        Action(thought="Notes say auth OK, billing is an offender, search still TODO. Resume there.",
               tool="read", args={"path": "services/search.cfg"}),
        Action(thought="search clean. Finalize the report from notes + this last check.",
               tool="write", args={"path": "REPORT.md",
                                   "content": "# TLS audit\n\nOffenders:\n- billing (tls=off)\n\nClean: auth, search\n"}),
        Action(thought="Report written and grounded in journaled evidence.",
               final="COMPLETE: 1 offender (billing). Full report in REPORT.md."),
    ]

    with tempfile.TemporaryDirectory(prefix="harness_demo2b_") as ws:
        toolbox = Toolbox(Path(ws))
        seed_workspace(toolbox)

        AgentLoop(ScriptedModel(session1), toolbox, trace, context_limit=3).run(TASK)
        trace.section("!! CONTEXT RESET — new session, zero conversation history !!")
        trace.note("(compaction, crash, or a fresh container — long-horizon work must survive this)")
        AgentLoop(ScriptedModel(session2), toolbox, trace, context_limit=3).run(TASK + " (resumed)")

        report = toolbox.read("REPORT.md")
        ok = "billing" in report and "auth" not in report.split("Offenders:")[1].split("Clean:")[0]
        trace.note("REPORT.md as written on disk:")
        for line in report.splitlines():
            trace.note(f"  | {line}")
        trace.verdict(ok, "report survived the reset and names exactly the right offender")


def main() -> None:
    trace = Trace(agent="demo")
    trace.banner(
        "DEMO 2 — File System as Persistent Memory",
        "same task, same tiny context window; the only difference is a notes file",
    )
    trace.intro(
        what="Why agent harnesses treat the file system as long-term memory instead of "
             "relying on the context window, which is small and gets evicted.",
        watch="The same audit task run twice under a tiny 3-message context window. Run "
              "A (red) keeps its findings only in context and loses them once they scroll "
              "out, finishing with an incomplete answer. Run B (green) journals findings "
              "to NOTES.md, survives a hard context reset into a brand-new session, and "
              "finishes with a correct report recovered entirely from disk.",
    )
    run_without_memory()
    run_with_memory()
    trace.takeaway([
        "Context windows are working memory; files are long-term memory.",
        "Journal findings as you go — any artifact worth keeping goes to disk.",
        "Writing files is a core LLM skill, so better models get better at memory for free.",
    ])


if __name__ == "__main__":
    main()
