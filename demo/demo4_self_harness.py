"""Demo 4 — Self-improving harness (Self-Harness loop, Zhang et al. 2026).

Article section: "Harness Optimization > Self-improving harness"

A toy agent's behavior is fully determined by its harness config (an
ordered list of named rules). The improvement loop is REAL, not scripted:

  1. WEAKNESS MINING   run the held-in suite, cluster failures by root cause
  2. HARNESS PROPOSAL  pick a bounded edit (add one rule) targeting the
                       biggest failure cluster
  3. VALIDATION        re-evaluate on held-in AND a held-out regression
                       suite; merge only if held-in improves and held-out
                       does not regress

One candidate rule is a classic reward hack — it aces the held-in cluster
by hardcoding an answer shape, and the held-out gate rejects it. That is
the article's point about evaluators living outside the optimization loop.
"""

from dataclasses import dataclass

from mini_harness import Trace
from mini_harness.trace import BOLD, DIM, GREEN, RED, YELLOW, paint

# --------------------------------------------------------------------------
# The "agent": normalizes messy money strings to canonical "12.50 USD" form.
# Its skill level is exactly its harness: an ordered list of rule names.
# --------------------------------------------------------------------------

def run_agent(harness: list[str], raw: str) -> str:
    value = raw
    if "strip_whitespace" in harness:
        value = value.strip()
    if "hack_assume_usd" in harness:
        # Reward hack: ignore the actual currency, always answer USD.
        digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
        return f"{float(digits):.2f} USD" if digits else value
    if "parse_currency_symbol" in harness:
        for symbol, code in (("$", "USD"), ("€", "EUR"), ("£", "GBP")):
            if symbol in value:
                value = value.replace(symbol, "").strip() + " " + code
    if "handle_comma_thousands" in harness:
        head = value.split(" ")[0].replace(",", "")
        value = head + (" " + value.split(" ", 1)[1] if " " in value else "")
    if "two_decimal_places" in harness:
        parts = value.split(" ")
        try:
            parts[0] = f"{float(parts[0]):.2f}"
            value = " ".join(parts)
        except ValueError:
            pass
    return value


@dataclass(frozen=True)
class Case:
    raw: str
    expected: str
    cluster: str  # failure cluster label used by weakness mining


HELD_IN = [
    Case("  12.5 USD ", "12.50 USD", "whitespace/decimals"),
    Case("7 USD", "7.00 USD", "whitespace/decimals"),
    Case("$3.1", "3.10 USD", "currency-symbol"),
    Case("$250", "250.00 USD", "currency-symbol"),
    Case("1,200 USD", "1200.00 USD", "thousands-separator"),
    Case("9,999.5 USD", "9999.50 USD", "thousands-separator"),
]

HELD_OUT = [  # regression suite — includes non-USD cases the hack would break
    Case("44 EUR", "44.00 EUR", "currency-symbol"),
    Case("3.5 GBP", "3.50 GBP", "currency-symbol"),
    Case(" 2 USD", "2.00 USD", "whitespace/decimals"),
    Case("8,000.25 USD", "8000.25 USD", "thousands-separator"),
]

# Bounded proposal space: candidate rules the proposer may add, keyed by the
# failure cluster they claim to address. First match is tried first.
CANDIDATES = {
    "whitespace/decimals": ["strip_whitespace", "two_decimal_places"],
    "currency-symbol": ["hack_assume_usd", "parse_currency_symbol"],
    "thousands-separator": ["handle_comma_thousands"],
}


def evaluate(harness: list[str], suite: list[Case]) -> tuple[int, dict[str, list[Case]]]:
    passed, clusters = 0, {}
    for case in suite:
        if run_agent(harness, case.raw) == case.expected:
            passed += 1
        else:
            clusters.setdefault(case.cluster, []).append(case)
    return passed, clusters


def main() -> None:
    trace = Trace(agent="self-harness", color=YELLOW)
    trace.banner(
        "DEMO 4 — A Harness That Improves Itself",
        "weakness mining -> bounded proposal -> validation gate (held-in + held-out)",
    )
    trace.note("Nothing here is scripted: failures, proposals, and accept/reject are computed live.")

    harness: list[str] = ["strip_whitespace"]  # h_0: minimal starting harness
    tried: set[str] = set()

    for iteration in range(1, 9):
        trace.section(f"iteration {iteration} — current harness h_{iteration - 1}: {harness}")

        # 1. Weakness mining
        in_score, clusters = evaluate(harness, HELD_IN)
        out_score, _ = evaluate(harness, HELD_OUT)
        trace.note(f"held-in {in_score}/{len(HELD_IN)}   held-out {out_score}/{len(HELD_OUT)}")
        if in_score == len(HELD_IN) and out_score == len(HELD_OUT):
            trace.final("All suites green — no weaknesses left to mine. Loop terminates.")
            break
        biggest = max(clusters, key=lambda c: len(clusters[c]))
        trace.thought(f"Weakness mining: {len(clusters[biggest])} failures cluster on '{biggest}' "
                      f"(e.g. {clusters[biggest][0].raw!r} -> "
                      f"{run_agent(harness, clusters[biggest][0].raw)!r}, "
                      f"expected {clusters[biggest][0].expected!r})")

        # 2. Bounded harness proposal
        proposal = next((r for r in CANDIDATES[biggest] if r not in tried and r not in harness), None)
        if proposal is None:
            trace.thought("No untried candidates for this cluster; stopping.")
            break
        tried.add(proposal)
        candidate = harness + [proposal]
        trace.thought(f"Proposal: h + ['{proposal}'] — a narrow, reviewable edit")

        # 3. Validation: held-in must improve, held-out must not regress
        new_in, _ = evaluate(candidate, HELD_IN)
        new_out, _ = evaluate(candidate, HELD_OUT)
        improves = new_in > in_score
        regresses = new_out < out_score
        trace.note(f"candidate scores: held-in {in_score}->{new_in}, held-out {out_score}->{new_out}")

        if improves and not regresses:
            harness = candidate
            trace.verdict(True, paint(f"MERGED: '{proposal}' accepted into h_{iteration}", GREEN, BOLD))
        else:
            reason = "regresses held-out (reward hack caught!)" if regresses else "does not improve held-in"
            trace.verdict(False, paint(f"REJECTED: '{proposal}' — {reason}; harness unchanged", RED, BOLD))
            trace.note(paint("rejected candidates are logged, not merged — the active harness never regresses", DIM))

    trace.section("final harness")
    trace.note(f"h_final = {harness}")
    in_score, _ = evaluate(harness, HELD_IN)
    out_score, _ = evaluate(harness, HELD_OUT)
    trace.verdict(in_score == len(HELD_IN) and out_score == len(HELD_OUT),
                  f"held-in {in_score}/{len(HELD_IN)}, held-out {out_score}/{len(HELD_OUT)}")

    trace.takeaway([
        "The improvement loop only trusts measurements, never intentions.",
        "The held-out gate caught 'hack_assume_usd' — evaluators must sit OUTSIDE the loop being optimized.",
        "Each edit is bounded and reviewable: this is version control discipline applied to the harness itself.",
    ])


if __name__ == "__main__":
    main()
