"""The "model": a deterministic script of thoughts and tool calls.

A real harness would POST the conversation to an LLM here. For a live,
reproducible, key-free demo we replay a plausible trajectory instead.
The harness around it (loop, tools, context management) doesn't know the
difference — which is exactly the abstraction boundary the article draws
between core intelligence and the harness layer.
"""

from dataclasses import dataclass, field


@dataclass
class Action:
    thought: str
    tool: str | None = None
    args: dict = field(default_factory=dict)
    final: str | None = None


class ScriptedModel:
    def __init__(self, script: list[Action]):
        self.script = list(script)
        self.cursor = 0

    def next_action(self, history: list[str]) -> Action:
        """`history` is the context window the harness chose to show us.

        A live model would condition on it; the script ignores it, but the
        loop still assembles it faithfully so you can inspect what a real
        model *would* have seen (demo 2 makes that visible).
        """
        if self.cursor >= len(self.script):
            return Action(thought="Script exhausted.", final="stopping")
        action = self.script[self.cursor]
        self.cursor += 1
        return action
