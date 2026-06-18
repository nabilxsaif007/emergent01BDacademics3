"""The runner is the seam between the dashboard and whatever actually does work.

Two implementations live here:

* `MockRunner` simulates an agent thinking, calling tools, burning tokens, and
  replying — so the whole command center (live feed, cost panels, timeline) is
  populated with realistic data out of the box.
* `RealRunner` drives the actual Claude Agent SDK. It's selected automatically
  when `claude_agent_sdk` is importable and credentials are present; otherwise
  we fall back to the mock so the app always runs.

Everything streams through the same `emit(kind, payload)` callback, so the rest
of the app never needs to know which runner is active.
"""
from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Awaitable, Callable, Protocol

from .models import ChatMessage, LogLevel, LogLine

# emit(kind, payload) -> the manager turns these into DB writes + WS broadcasts.
#   "log"      -> LogLine
#   "message"  -> ChatMessage
#   "progress" -> int (0-100)
#   "usage"    -> {"tokens_in": int, "tokens_out": int}
Emit = Callable[[str, object], Awaitable[None]]


# Rough public per-1M-token prices (USD), input/output. Used to turn token
# usage into a cost the dashboard can show. Keep approximate; easy to tune.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
}


def cost_for(model: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    return (tokens_in * pin + tokens_out * pout) / 1_000_000


class Runner(Protocol):
    async def run(self, prompt: str, emit: Emit) -> None:
        """Process `prompt`, streaming logs/messages via `emit`. Should end by
        emitting a final ('message', ChatMessage) from the agent."""
        ...


# --------------------------------------------------------------------------- #
# Mock runner
# --------------------------------------------------------------------------- #

class MockRunner:
    """Fakes an agent working a task so the dashboard feels alive end-to-end.

    Emits realistic tool calls (with durations) and token usage so the cost,
    timeline, and live-feed panels all have genuine data to render.
    """

    async def run(self, prompt: str, emit: Emit) -> None:
        steps = self._plan(prompt)
        total = len(steps)
        for i, step in enumerate(steps, start=1):
            kind = step[0]
            if kind == "think":
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await emit("log", LogLine(level=LogLevel.info, text=step[1]))
                await self._burn(emit, 200, 700, 30, 120)
            elif kind == "tool":
                _, name, arg = step
                t0 = time.monotonic()
                await asyncio.sleep(random.uniform(0.5, 1.4))  # tool "runs"
                dur = int((time.monotonic() - t0) * 1000)
                await emit(
                    "log",
                    LogLine(level=LogLevel.tool, text=f"{name}({arg})", tool=name, dur_ms=dur),
                )
                await self._burn(emit, 400, 1600, 80, 400)
            elif kind == "success":
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await emit("log", LogLine(level=LogLevel.success, text=step[1]))
            await emit("progress", int(i / total * 100))

        # small chance of a simulated failure so the 'failed' state is exercised
        if random.random() < 0.05:
            await emit("log", LogLine(level=LogLevel.error, text="Task failed: simulated tool error"))
            raise RuntimeError("simulated failure")

        await self._burn(emit, 300, 900, 200, 800)
        await emit("message", ChatMessage(role="agent", content=self._reply(prompt)))

    async def _burn(self, emit: Emit, in_lo: int, in_hi: int, out_lo: int, out_hi: int) -> None:
        await emit(
            "usage",
            {
                "tokens_in": random.randint(in_lo, in_hi),
                "tokens_out": random.randint(out_lo, out_hi),
            },
        )

    def _plan(self, prompt: str) -> list[tuple]:
        p = prompt.lower()
        steps: list[tuple] = [
            ("think", f"Received task: {prompt[:80]}"),
            ("think", "Breaking the task into steps..."),
        ]
        if any(k in p for k in ("code", "bug", "fix", "function", "refactor", "build", "test")):
            steps += [
                ("tool", "read_files", "src/"),
                ("think", "Analyzing the relevant modules..."),
                ("tool", "edit_file", "src/main.py"),
                ("tool", "run_tests", "pytest -q"),
                ("success", "Tests passed (12/12)"),
            ]
        elif any(k in p for k in ("research", "find", "search", "look up", "investigate")):
            steps += [
                ("tool", "web_search", "query=..."),
                ("think", "Reading 5 sources..."),
                ("tool", "fetch_url", "3 pages"),
                ("tool", "summarize", "notes"),
            ]
        elif any(k in p for k in ("deploy", "build", "ops", "ci", "pipeline", "release")):
            steps += [
                ("tool", "docker_build", "image:latest"),
                ("think", "Pushing image to registry..."),
                ("tool", "kubectl_apply", "staging"),
                ("success", "Deployed to staging"),
            ]
        elif any(k in p for k in ("write", "draft", "doc", "notes", "summary", "blog")):
            steps += [
                ("think", "Outlining the structure..."),
                ("tool", "draft", "section 1-4"),
                ("tool", "polish", "tone + grammar"),
            ]
        else:
            steps += [
                ("think", "Working through the request..."),
                ("tool", "execute", "plan"),
            ]
        steps.append(("success", "Done."))
        return steps

    def _reply(self, prompt: str) -> str:
        return (
            f"Finished working on: \"{prompt[:120]}\".\n"
            "(Mocked response — set ANTHROPIC_API_KEY and install claude-agent-sdk "
            "to switch this agent to real execution.)"
        )


# --------------------------------------------------------------------------- #
# Real runner (Claude Agent SDK)
# --------------------------------------------------------------------------- #

class RealRunner:
    """Drives the actual Claude Agent SDK, streaming its turns through `emit`.

    Kept defensive: any import/runtime issue is surfaced as an error log and the
    task fails cleanly rather than taking the process down.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self.model = model

    async def run(self, prompt: str, emit: Emit) -> None:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions  # type: ignore

        await emit("log", LogLine(level=LogLevel.info, text=f"Received task: {prompt[:80]}"))
        options = ClaudeAgentOptions(model=self.model)
        reply_parts: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                await self._handle(message, emit, reply_parts)

        final = "".join(reply_parts).strip() or "Done."
        await emit("message", ChatMessage(role="agent", content=final))
        await emit("progress", 100)

    async def _handle(self, message, emit: Emit, reply_parts: list[str]) -> None:
        # The SDK yields content blocks; we translate the ones we care about.
        blocks = getattr(message, "content", None)
        if blocks is None:
            return
        for block in blocks:
            btype = type(block).__name__
            if btype == "TextBlock":
                txt = getattr(block, "text", "")
                reply_parts.append(txt)
                if txt.strip():
                    await emit("log", LogLine(level=LogLevel.info, text=txt.strip()[:200]))
            elif btype == "ToolUseBlock":
                name = getattr(block, "name", "tool")
                await emit("log", LogLine(level=LogLevel.tool, text=f"{name}(...)", tool=name))
        # usage, when present on the message
        usage = getattr(message, "usage", None)
        if usage:
            await emit(
                "usage",
                {
                    "tokens_in": int(getattr(usage, "input_tokens", 0) or 0),
                    "tokens_out": int(getattr(usage, "output_tokens", 0) or 0),
                },
            )


def _real_available() -> bool:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("USE_REAL_RUNNER")):
        return False
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except Exception:
        return False


def get_runner(model: str = "claude-sonnet-4-6") -> Runner:
    """Single place to choose the active runner implementation."""
    if _real_available():
        return RealRunner(model=model)
    return MockRunner()
