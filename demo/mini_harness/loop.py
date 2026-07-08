"""The agent loop — the heart of every harness.

plan -> act (tool call) -> observe -> repeat, until the model declares done
or the step budget runs out. Also owns context assembly: it decides what
slice of history the model sees each turn (`context_limit`), which demo 2
uses to show why filesystem memory matters.
"""

from dataclasses import dataclass

from .model import ScriptedModel
from .tools import Toolbox
from .trace import Trace


@dataclass
class LoopResult:
    final: str
    turns: int
    history: list[str]


class AgentLoop:
    def __init__(
        self,
        model: ScriptedModel,
        toolbox: Toolbox,
        trace: Trace,
        max_turns: int = 25,
        context_limit: int | None = None,
    ):
        self.model = model
        self.toolbox = toolbox
        self.trace = trace
        self.max_turns = max_turns
        self.context_limit = context_limit

    def run(self, task: str) -> LoopResult:
        history: list[str] = [f"TASK: {task}"]
        for turn in range(1, self.max_turns + 1):
            context = self._assemble_context(history)
            action = self.model.next_action(context)
            self.trace.turn(turn)
            self.trace.thought(action.thought)

            if action.final is not None:
                self.trace.final(action.final)
                return LoopResult(final=action.final, turns=turn, history=history)

            detail = ", ".join(f"{k}={self._short(v)}" for k, v in action.args.items())
            self.trace.tool(action.tool, detail)
            try:
                observation = self.toolbox.call(action.tool, **action.args)
            except Exception as exc:  # surfaced to the model, like a real harness
                observation = f"TOOL ERROR: {exc}"
            self.trace.observation(observation)
            history.append(f"{action.tool}({detail}) -> {observation}")

        return LoopResult(final="step budget exhausted", turns=self.max_turns, history=history)

    def _assemble_context(self, history: list[str]) -> list[str]:
        if self.context_limit is None or len(history) <= self.context_limit:
            return history
        # Task always survives; the middle falls out of the window.
        return [history[0]] + history[-(self.context_limit - 1):]

    @staticmethod
    def _short(value, limit: int = 48) -> str:
        text = repr(value)
        return text if len(text) <= limit else text[: limit - 3] + "..."
