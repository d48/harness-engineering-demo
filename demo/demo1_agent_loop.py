"""Demo 1 — Pattern 1: Workflow automation (the agent loop).

Article section: "Harness Design Patterns > Workflow automation"

A sandbox repo contains a real bug and a real failing test. The loop runs
plan -> act -> observe -> improve until the test suite is green. The model
is scripted, but the files, the edit, and the pytest-style run are real —
the final PASS is earned, not printed.
"""

import tempfile
from pathlib import Path

from mini_harness import Action, AgentLoop, ScriptedModel, Toolbox, Trace

BUGGY_MODULE = '''\
def median(values):
    """Return the median of a list of numbers."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid]
'''

TEST_FILE = '''\
from stats import median

def check(actual, expected):
    assert actual == expected, f"expected {expected}, got {actual}"

check(median([5, 1, 3]), 3)
check(median([7]), 7)
check(median([1, 2, 3, 4]), 2.5)   # even-length list: mean of the middle two
print("all tests passed")
'''

SCRIPT = [
    Action(
        thought="New task. First, orient: what files are in this repo?",
        tool="ls", args={"path": "."},
    ),
    Action(
        thought="Run the test suite before touching anything — establish the failure.",
        tool="bash", args={"cmd": "python3 test_stats.py"},
    ),
    Action(
        thought="AssertionError on the even-length case. Let me read the implementation.",
        tool="read", args={"path": "stats.py"},
    ),
    Action(
        thought=(
            "Found it: for even-length input it returns the upper-middle element "
            "instead of averaging the two middle elements. Patch the return."
        ),
        tool="edit",
        args={
            "path": "stats.py",
            "old": "    return ordered[mid]",
            "new": (
                "    if len(ordered) % 2 == 1:\n"
                "        return ordered[mid]\n"
                "    return (ordered[mid - 1] + ordered[mid]) / 2"
            ),
        },
    ),
    Action(
        thought="Verify: re-run the tests. Never claim success without observing it.",
        tool="bash", args={"cmd": "python3 test_stats.py"},
    ),
    Action(
        thought="Exit code 0 and 'all tests passed' — the fix is verified.",
        final="Fixed median() for even-length lists; test suite is green.",
    ),
]


def main() -> None:
    trace = Trace(agent="coder")
    trace.banner(
        "DEMO 1 — The Agent Loop (workflow automation)",
        "plan -> act -> observe -> improve, until the goal is verifiably met",
    )
    trace.intro(
        what="The canonical coding-agent loop — plan, act, observe, improve — repeated "
             "until a goal is verifiably met. It's the same loop shape shared by Claude "
             "Code, Codex, OpenCode, and Cursor.",
        watch="A sandboxed repo with a real bug and a real failing test. The scripted "
              "'model' inspects the repo, runs the tests, finds the bug, patches it, and "
              "re-runs the tests — then the harness independently re-checks the fix "
              "before declaring success.",
    )
    trace.note("The 'model' is a deterministic script; the tools and test run are real.")

    with tempfile.TemporaryDirectory(prefix="harness_demo1_") as ws:
        toolbox = Toolbox(Path(ws))
        toolbox.write("stats.py", BUGGY_MODULE)
        toolbox.write("test_stats.py", TEST_FILE)

        loop = AgentLoop(ScriptedModel(SCRIPT), toolbox, trace)
        loop.run("Tests in this repo are failing. Find the bug, fix it, prove it's fixed.")

        # The demo itself verifies the agent's claim — trust nothing.
        result = toolbox.bash("python3 test_stats.py")
        ok = result.startswith("exit=0")
        trace.verdict(ok, "harness-side re-check of the test suite (never trust the model's claim)")

    trace.takeaway([
        "The loop, not the model, enforces 'observe before you claim success'.",
        "Every observation is a real tool result fed back as context.",
        "This exact loop shape is shared by Claude Code, Codex, OpenCode, Cursor.",
    ])


if __name__ == "__main__":
    main()
