"""The runner is the seam between the dashboard and whatever actually does work.

Today it's a MockRunner that *simulates* an agent thinking, calling tools, and
replying. When you're ready for real work, implement `Runner.run` with the
Claude Agent SDK (claude_agent_sdk) and stream its messages/tool calls through
the same `emit` callback. Nothing else in the app has to change.
"""
from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, Protocol

from .models import ChatMessage, LogLevel, LogLine

# emit(kind, payload) -> the manager turns these into DB writes + WS broadcasts.
Emit = Callable[[str, object], Awaitable[None]]


class Runner(Protocol):
    async def run(self, prompt: str, emit: Emit) -> None:
        """Process `prompt`, streaming logs/messages via `emit`. Should end by
        emitting a final ('message', ChatMessage) from the agent."""
        ...


class MockRunner:
    """Fakes an agent working a task so the dashboard feels alive end-to-end."""

    async def run(self, prompt: str, emit: Emit) -> None:
        steps = self._plan(prompt)
        total = len(steps)
        for i, (level, text) in enumerate(steps, start=1):
            await asyncio.sleep(random.uniform(0.4, 1.1))
            await emit("log", LogLine(level=level, text=text))
            await emit("progress", int(i / total * 100))

        # tiny chance of a simulated failure so 'failed' state is exercised
        if random.random() < 0.06:
            await emit("log", LogLine(level=LogLevel.error, text="Task failed: simulated error"))
            raise RuntimeError("simulated failure")

        await emit("message", ChatMessage(role="agent", content=self._reply(prompt)))

    # --- mock content generation ---

    def _plan(self, prompt: str) -> list[tuple[LogLevel, str]]:
        p = prompt.lower()
        steps: list[tuple[LogLevel, str]] = [
            (LogLevel.info, f"Received task: {prompt[:80]}"),
            (LogLevel.info, "Breaking the task into steps..."),
        ]
        if any(k in p for k in ("code", "bug", "fix", "function", "refactor", "build")):
            steps += [
                (LogLevel.tool, "read_files(['src/'])"),
                (LogLevel.info, "Analyzing the relevant modules..."),
                (LogLevel.tool, "edit_file('src/main.py')"),
                (LogLevel.tool, "run_tests()"),
                (LogLevel.success, "Tests passed (12/12)"),
            ]
        elif any(k in p for k in ("research", "find", "search", "look up")):
            steps += [
                (LogLevel.tool, "web_search(query=...)"),
                (LogLevel.info, "Reading 5 sources..."),
                (LogLevel.tool, "summarize()"),
            ]
        else:
            steps += [
                (LogLevel.info, "Working through the request..."),
                (LogLevel.tool, "execute()"),
            ]
        steps.append((LogLevel.success, "Done."))
        return steps

    def _reply(self, prompt: str) -> str:
        return (
            f"Finished working on: \"{prompt[:120]}\".\n"
            "(This is a mocked response. Wire up the Claude Agent SDK in "
            "runner.py to make it real.)"
        )


def get_runner() -> Runner:
    """Single place to choose the active runner implementation."""
    return MockRunner()
