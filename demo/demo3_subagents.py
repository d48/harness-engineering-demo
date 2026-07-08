"""Demo 3 — Pattern 3: Sub-agents and background jobs.

Article section: "Harness Design Patterns > Sub-agent and backend jobs"

An orchestrator investigates a production bug by spawning three sub-agents
in parallel (real threads), one per hypothesis. Each explores in its own
lane, then writes findings to findings/<name>.md — files, not chat context,
so the parallelism stays inspectable. The orchestrator's context receives
only three short files instead of three full transcripts.
"""

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mini_harness import Action, AgentLoop, ScriptedModel, Toolbox, Trace
from mini_harness.trace import BLUE, CYAN, GREEN, YELLOW

APP_LOG = """\
2026-07-08 04:59:58 INFO  worker heartbeat ok
2026-07-08 05:00:01 ERROR payment worker crashed: KeyError: 'currency'
2026-07-08 05:00:01 INFO  restarting worker
2026-07-08 05:00:03 ERROR payment worker crashed: KeyError: 'currency'
"""

PAYMENTS_PY = """\
def process(payment):
    amount = payment["amount"]
    currency = payment["currency"]   # new field, added last week
    return f"{amount} {currency}"
"""

QUEUE_SAMPLE = '{"amount": 1200}\n{"amount": 900, "currency": "USD"}\n'

DEPLOY_LOG = "2026-07-01 deploy v41 payments-service (add currency support)\n"

# One print lock so interleaved thread output stays line-atomic.
PRINT_LOCK = threading.Lock()


class LockedTrace(Trace):
    def _emit(self, line: str = "") -> None:
        with PRINT_LOCK:
            super()._emit(line)


def subagent(name: str, color: str, toolbox: Toolbox, script: list[Action], task: str) -> str:
    trace = LockedTrace(agent=name, color=color, delay=0.25)
    loop = AgentLoop(ScriptedModel(script), toolbox, trace)
    return loop.run(task).final


HYPOTHESES = {
    "sub-logs": (
        YELLOW,
        "Hypothesis: the crash signature is in the app logs.",
        [
            Action(thought="Grep the logs for stack traces or ERROR lines.",
                   tool="grep", args={"pattern": "ERROR", "path": "logs/app.log"}),
            Action(thought="Repeated KeyError: 'currency' in the payment worker. Write findings.",
                   tool="write", args={"path": "findings/sub-logs.md",
                                       "content": "SIGNAL: worker crash-loops with KeyError: 'currency'\nconfidence: high\n"}),
            Action(thought="Findings persisted for the orchestrator.", final="KeyError: 'currency' crash loop"),
        ],
    ),
    "sub-code": (
        BLUE,
        "Hypothesis: a recent code change reads a field that isn't always present.",
        [
            Action(thought="Search the codebase for 'currency'.",
                   tool="grep", args={"pattern": "currency", "path": "src"}),
            Action(thought="process() indexes payment['currency'] with no default. Read it in full.",
                   tool="read", args={"path": "src/payments.py"}),
            Action(thought="Confirmed unguarded dict access on a new field. Write findings.",
                   tool="write", args={"path": "findings/sub-code.md",
                                       "content": "ROOT CAUSE CANDIDATE: src/payments.py reads payment['currency'] "
                                                  "without a default; field added in v41.\nconfidence: high\n"}),
            Action(thought="Done.", final="unguarded payment['currency'] access"),
        ],
    ),
    "sub-data": (
        CYAN,
        "Hypothesis: bad messages in the queue are triggering it.",
        [
            Action(thought="Inspect a sample of queued payment messages.",
                   tool="read", args={"path": "queue/sample.jsonl"}),
            Action(thought="First message predates v41 and has no 'currency' key — old messages still in flight. Write findings.",
                   tool="write", args={"path": "findings/sub-data.md",
                                       "content": "TRIGGER: pre-v41 queue messages lack 'currency'; they hit the new code path.\nconfidence: high\n"}),
            Action(thought="Done.", final="legacy queue messages lack 'currency'"),
        ],
    ),
}


def main() -> None:
    trace = Trace(agent="orchestrator", color=GREEN)
    trace.banner(
        "DEMO 3 — Sub-agents in Parallel",
        "three hypotheses, three isolated agents, results merged via the file system",
    )
    trace.intro(
        what="How a harness fans work out to sub-agents and fans results back in without "
             "polluting the parent's context — the pattern behind Claude Code's Agent "
             "tool and background jobs.",
        watch="Three sub-agents (real threads) investigate a crash-looping payment "
              "service in parallel, each chasing a different hypothesis: logs, code, and "
              "queue data. Each writes its findings to its own file; the orchestrator "
              "then reads just those three short files and synthesizes the root cause.",
    )

    with tempfile.TemporaryDirectory(prefix="harness_demo3_") as ws:
        toolbox = Toolbox(Path(ws))
        toolbox.write("logs/app.log", APP_LOG)
        toolbox.write("src/payments.py", PAYMENTS_PY)
        toolbox.write("queue/sample.jsonl", QUEUE_SAMPLE)
        toolbox.write("deploys/history.log", DEPLOY_LOG)

        trace.section("fan-out: spawn_agent x3 (real threads, interleaved output)")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                name: pool.submit(subagent, name, color, toolbox, script, hypothesis)
                for name, (color, hypothesis, script) in HYPOTHESES.items()
            }
            for future in futures.values():
                future.result()

        trace.section("fan-in: orchestrator reads findings/ — not transcripts")
        trace.note("Each sub-agent burned its own context; the parent pays only for these files:")
        for name in HYPOTHESES:
            content = toolbox.read(f"findings/{name}.md")
            trace.tool("read", f"path='findings/{name}.md'")
            trace.observation(content)

        trace.turn(1)
        trace.thought(
            "Synthesis: v41 added a required 'currency' field (code), old queue messages "
            "lack it (data), causing the crash loop (logs). Fix: payment.get('currency', 'USD') "
            "+ backfill, then drain the queue."
        )
        trace.final("Root cause triangulated from three parallel investigations.")

        ok = all(toolbox.read(f"findings/{n}.md").strip() for n in HYPOTHESES)
        trace.verdict(ok, "all three findings files exist on disk and are non-empty")

    trace.takeaway([
        "Parallel exploration without polluting the parent's context window.",
        "File-based hand-off keeps the fan-out inspectable and debuggable after the fact.",
        "Same pattern as Claude Code's Agent tool / background jobs: spawn, monitor, merge.",
    ])


if __name__ == "__main__":
    main()
