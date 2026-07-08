#!/usr/bin/env python3
"""Runner for the harness-engineering demos.

Usage:
    python3 demo/run.py           # interactive menu
    python3 demo/run.py 1         # run demo 1
    python3 demo/run.py all       # run every demo back to back
    python3 demo/run.py all --fast  # no dramatic pauses (CI / smoke test)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

MENU = """
  Harness Engineering — live demos
  (concepts from Lilian Weng, "Harness Engineering for Self-Improvement", Jul 2026)

    1. The agent loop           plan -> act -> observe -> improve (fixes a real failing test)
    2. Filesystem as memory     survive a tiny context window + a hard context reset
    3. Sub-agents in parallel   3 hypotheses, 3 threads, merged via findings/ files
    4. Self-improving harness   propose -> evaluate -> accept, reward hack caught by held-out gate
    5. Evolutionary search      evolve real code in an EVOLVE-BLOCK until MSE = 0

    a. run all      q. quit
"""


def run(number: str) -> None:
    import demo1_agent_loop
    import demo2_memory
    import demo3_subagents
    import demo4_self_harness
    import demo5_evolution

    demos = {
        "1": demo1_agent_loop.main,
        "2": demo2_memory.main,
        "3": demo3_subagents.main,
        "4": demo4_self_harness.main,
        "5": demo5_evolution.main,
    }
    if number in ("a", "all"):
        for main in demos.values():
            main()
    elif number in demos:
        demos[number]()
    else:
        print(f"unknown demo: {number}")
        sys.exit(2)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--fast"]
    if "--fast" in sys.argv:
        os.environ["DEMO_FAST"] = "1"

    if args:
        run(args[0])
        return

    while True:
        print(MENU)
        choice = input("  choose> ").strip().lower()
        if choice in ("q", "quit", "exit", ""):
            return
        run(choice)


if __name__ == "__main__":
    main()
