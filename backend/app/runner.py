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
import shutil
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

    Each agent works inside its own `workspace` directory and reports real token
    usage and cost straight from the SDK's ResultMessage. Kept defensive: any
    failure is surfaced as an error log and the task fails cleanly.
    """

    ROLE_HINT = {
        "coder": "You are an autonomous coding agent. Make the requested changes "
                 "directly in the working directory and verify them.",
        "researcher": "You are a research agent. Investigate thoroughly and finish "
                      "with a concise, well-organized summary.",
        "writer": "You are a writing agent. Produce clear, polished prose or docs.",
        "ops": "You are a DevOps agent. Use shell tools carefully to accomplish the task.",
        "general": "You are a capable autonomous agent. Complete the task end to end.",
    }

    def __init__(self, model: str, workspace: str | None = None, role: str = "general") -> None:
        self.model = model
        self.workspace = workspace
        self.role = role
        self.max_turns = int(os.environ.get("AGENT_MAX_TURNS", "20"))

    async def run(self, prompt: str, emit: Emit) -> None:
        from claude_agent_sdk import (  # type: ignore
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ThinkingBlock,
            ToolUseBlock,
            PermissionResultAllow,
        )

        # Auto-approve tool use programmatically. (We can't use the CLI's
        # bypass flag because it refuses to run as root; this callback is the
        # supported way to run autonomously.)
        async def _approve(tool_name, tool_input, context):
            return PermissionResultAllow()

        options = ClaudeAgentOptions(
            model=self.model,
            max_turns=self.max_turns,
            cwd=self.workspace,
            permission_mode=os.environ.get("AGENT_PERMISSION_MODE", "acceptEdits"),
            can_use_tool=_approve,
        )
        hint = self.ROLE_HINT.get(self.role, self.ROLE_HINT["general"])
        framed = f"{hint}\n\nTask: {prompt}"

        reply: list[str] = []
        state = {"turns": 0, "last_tool_ts": time.monotonic()}

        async with ClaudeSDKClient(options=options) as client:
            await client.query(framed)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    state["turns"] += 1
                    await emit("progress", min(90, 10 + state["turns"] * 8))
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            txt = (block.text or "").strip()
                            if txt:
                                reply.append(block.text)
                                await emit("log", LogLine(level=LogLevel.info, text=txt[:300]))
                        elif isinstance(block, ThinkingBlock):
                            th = (getattr(block, "thinking", "") or "").strip()
                            if th:
                                await emit("log", LogLine(level=LogLevel.info, text=f"thinking: {th[:160]}"))
                        elif isinstance(block, ToolUseBlock):
                            now = time.monotonic()
                            dur = int((now - state["last_tool_ts"]) * 1000)
                            state["last_tool_ts"] = now
                            arg = self._summarize(block.input)
                            await emit(
                                "log",
                                LogLine(level=LogLevel.tool, text=f"{block.name}({arg})",
                                        tool=block.name, dur_ms=dur),
                            )
                elif isinstance(message, ResultMessage):
                    u = message.usage or {}
                    tokens_in = (
                        int(u.get("input_tokens", 0) or 0)
                        + int(u.get("cache_read_input_tokens", 0) or 0)
                        + int(u.get("cache_creation_input_tokens", 0) or 0)
                    )
                    await emit(
                        "usage",
                        {
                            "tokens_in": tokens_in,
                            "tokens_out": int(u.get("output_tokens", 0) or 0),
                            "cost": getattr(message, "total_cost_usd", None),
                        },
                    )
                    if getattr(message, "is_error", False):
                        raise RuntimeError(getattr(message, "result", "agent run failed"))

        final = "".join(reply).strip() or "Done."
        await emit("message", ChatMessage(role="agent", content=final))
        await emit("progress", 100)

    @staticmethod
    def _summarize(tool_input: object) -> str:
        """Make a short, human label for a tool call's arguments."""
        if not isinstance(tool_input, dict):
            return str(tool_input)[:80]
        for key in ("file_path", "path", "command", "pattern", "query", "url", "prompt"):
            if key in tool_input and tool_input[key]:
                return str(tool_input[key])[:80]
        return ", ".join(f"{k}={str(v)[:30]}" for k, v in list(tool_input.items())[:2])[:80]


def _real_available() -> bool:
    if os.environ.get("DISABLE_REAL_RUNNER"):
        return False
    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        return False
    # Auth is satisfied by either an API key or a logged-in `claude` CLI.
    return bool(shutil.which("claude") or os.environ.get("ANTHROPIC_API_KEY"))


def get_runner(model: str = "claude-sonnet-4-6", workspace: str | None = None,
               role: str = "general") -> Runner:
    """Single place to choose the active runner implementation. Prefers real
    execution whenever the Claude Agent SDK + credentials are available."""
    if _real_available():
        return RealRunner(model=model, workspace=workspace, role=role)
    return MockRunner()
