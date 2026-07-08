"""mini_harness — a deliberately tiny agent harness for teaching purposes.

The "model" is scripted (deterministic, no API key needed) but everything
around it is real: real files, real subprocesses, real test runs, real
parallelism, real accept/reject gates. That asymmetry is the point of the
demo — the harness is genuine machinery, and you could swap the scripted
model for a live LLM without touching the rest.
"""

from .loop import AgentLoop
from .model import Action, ScriptedModel
from .tools import Toolbox
from .trace import Trace

__all__ = ["Action", "AgentLoop", "ScriptedModel", "Toolbox", "Trace"]
