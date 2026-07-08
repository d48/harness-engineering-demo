"""Demo 5 — Evolutionary search over programs (AlphaEvolve / Darwin Gödel Machine flavor).

Article section: "Harness Optimization > Evolutionary search"

We evolve the body of a real Python function between EVOLVE-BLOCK markers.
The task: rediscover an unknown pricing formula from input/output examples
(symbolic regression). Each generation, parents are sampled from the
population, mutated (playing the role of LLM-proposed diffs), executed,
and scored against the examples — real fitness, real selection, no LLM
required, fully deterministic under a fixed seed.

Diversity preservation (keep structurally distinct genomes, sample parents
beyond just the best) is what stops the population collapsing onto one
mediocre formula — the article's bottleneck #4.
"""

import random

from mini_harness import Trace
from mini_harness.trace import BOLD, DIM, GREEN, paint

# The hidden target the evolved program must rediscover: price = x*x + 3x + 2
EXAMPLES = [(x, x * x + 3 * x + 2) for x in range(-5, 6)]

TEMPLATE = """\
def predict_price(x):
    # EVOLVE-BLOCK-START
    return {expr}
    # EVOLVE-BLOCK-END
"""

TERMINALS = ["x", "1", "2", "3"]
OPERATORS = ["+", "-", "*"]


def random_expr(rng: random.Random, depth: int = 0) -> str:
    if depth >= 3 or rng.random() < 0.3:
        return rng.choice(TERMINALS)
    op = rng.choice(OPERATORS)
    return f"({random_expr(rng, depth + 1)} {op} {random_expr(rng, depth + 1)})"


def mutate(expr: str, rng: random.Random) -> str:
    """Stand-in for an LLM proposing a diff to the evolve block."""
    roll = rng.random()
    if roll < 0.4:  # graft: combine with a fresh subexpression
        return f"({expr} {rng.choice(OPERATORS)} {random_expr(rng, 2)})"
    if roll < 0.7:  # point mutation: swap one token
        tokens = expr.replace("(", " ( ").replace(")", " ) ").split()
        idx = rng.randrange(len(tokens))
        if tokens[idx] in TERMINALS:
            tokens[idx] = rng.choice(TERMINALS)
        elif tokens[idx] in OPERATORS:
            tokens[idx] = rng.choice(OPERATORS)
        return " ".join(tokens).replace("( ", "(").replace(" )", ")")
    return random_expr(rng)  # fresh restart — an immigrant genome


def fitness(expr: str) -> float:
    """Mean squared error against the examples; the real, external evaluator."""
    namespace: dict = {}
    try:
        exec(TEMPLATE.format(expr=expr), namespace)  # genuinely runs the program
        err = sum((namespace["predict_price"](x) - y) ** 2 for x, y in EXAMPLES)
        return err / len(EXAMPLES)
    except Exception:
        return float("inf")


def main() -> None:
    trace = Trace(agent="evolver", color=GREEN, delay=0.15)
    trace.banner(
        "DEMO 5 — Evolutionary Search over Program Code",
        "mutate the EVOLVE-BLOCK, execute, score, select — survival of the fittest diff",
    )
    trace.note("Hidden target: price(x) = x*x + 3x + 2   (the evolver only sees input/output pairs)")
    trace.note("Every candidate is real code, exec'd and scored on the examples (MSE).")

    rng = random.Random(7)
    population = [(random_expr(rng), 0.0) for _ in range(12)]
    population = [(e, fitness(e)) for e, _ in population]

    trace.section("generation 0 — random population")
    for expr, fit in sorted(population, key=lambda p: p[1])[:3]:
        trace.note(f"MSE {fit:10.2f}   return {expr}")

    best_expr, best_fit = min(population, key=lambda p: p[1])
    for gen in range(1, 41):
        # Parent sampling: weighted toward fitness but not winner-take-all,
        # so distinct lineages survive (diversity preservation).
        ranked = sorted(population, key=lambda p: p[1])
        parents = [ranked[i][0] for i in (0, 1, 2, rng.randrange(len(ranked)))]

        children = []
        for parent in parents:
            for _ in range(4):
                child = mutate(parent, rng)
                children.append((child, fitness(child)))

        # Survivor selection with a novelty guard: no duplicate genomes.
        pool = {expr: fit for expr, fit in population + children}
        population = sorted(pool.items(), key=lambda p: p[1])[:12]

        gen_best_expr, gen_best_fit = population[0]
        if gen_best_fit < best_fit:
            best_expr, best_fit = gen_best_expr, gen_best_fit
            trace._emit(
                f"  gen {gen:>3}  " + paint(f"MSE {best_fit:10.2f}", BOLD)
                + f"   return {best_expr}"
            )
            trace.pause()
        if best_fit == 0.0:
            break

    trace.section("champion program (exact fit found)" if best_fit == 0.0 else "best program found")
    for line in TEMPLATE.format(expr=best_expr).splitlines():
        trace.note(paint(line, BOLD) if "return" in line else paint(line, DIM))

    checks = all(
        eval(best_expr, {"x": x}) == y  # noqa: S307 — same sandboxed expr we evolved
        for x, y in EXAMPLES
    ) if best_fit == 0.0 else False
    trace.verdict(checks, "champion reproduces every example exactly (MSE = 0)")

    trace.takeaway([
        "Code is a universal search space: mutate -> execute -> measure needs no gradients.",
        "This works because the evaluator is fast and objective — the article's precondition.",
        "AlphaEvolve does exactly this with an LLM proposing the diffs; DGM applies it to the agent's own harness code.",
    ])


if __name__ == "__main__":
    main()
