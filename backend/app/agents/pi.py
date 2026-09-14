"""Small, dependency-free bridge to the official Pi Coding Agent RPC CLI."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("app.agents.pi")


class PiError(RuntimeError):
    """Safe operational error raised when the Pi CLI cannot complete."""


@dataclass(frozen=True)
class PiResult:
    text: str
    provider: str | None
    model: str | None


class PiBridge:
    """Invoke ``pi --mode rpc`` and extract the final assistant text.

    Pi's RPC transport is JSON Lines.  This bridge intentionally keeps the
    protocol boundary here so API callers never see process output or errors.
    """

    def __init__(self, command: str = "pi", provider: str = "", model: str = "", timeout_seconds: float = 60.0) -> None:
        self.command = command
        self.provider = provider
        self.model = model
        self.timeout_seconds = timeout_seconds

    def run(self, prompt: str) -> PiResult:
        command = [self.command, "--mode", "rpc", "--no-session"]
        if self.provider:
            command.extend(["--provider", self.provider])
        if self.model:
            command.extend(["--model", self.model])

        # The RPC mode accepts a prompt event per line.  The agent receives
        # only operational context; transcript evidence/final prose remain in
        # the deterministic grounded-answer path.
        request = json.dumps({"type": "prompt", "message": prompt}) + "\n"
        start = time.monotonic()
        logger.info("Pi invocation started: provider=%s model=%s", self.provider or "default", self.model or "default")
        try:
            completed = subprocess.run(
                command,
                input=request,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            logger.warning("Pi invocation failed: executable unavailable")
            raise PiError("Pi Coding Agent is unavailable. Check PI_COMMAND and install Pi.") from exc
        except subprocess.TimeoutExpired as exc:
            logger.warning("Pi invocation timed out: timeout_seconds=%s", self.timeout_seconds)
            raise PiError("Pi Coding Agent timed out. Try again or increase PI_TIMEOUT_SECONDS.") from exc
        except OSError as exc:
            logger.warning("Pi invocation failed: process error=%s", exc.__class__.__name__)
            raise PiError("Pi Coding Agent could not be started.") from exc

        result = self._parse_output(completed.stdout)
        if completed.returncode != 0:
            logger.warning("Pi invocation failed: exit_code=%s", completed.returncode)
            raise PiError("Pi Coding Agent failed to complete the request.")
        if result is None:
            logger.warning("Pi invocation failed: malformed RPC output")
            raise PiError("Pi Coding Agent returned an unexpected response.")
        logger.info("Pi invocation complete: duration=%.3fs success=True", time.monotonic() - start)
        return PiResult(text=result, provider=self.provider or None, model=self.model or None)

    @staticmethod
    def _parse_output(output: str) -> str | None:
        texts: list[str] = []
        for line in output.splitlines():
            try:
                event: Any = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("success") is False or event.get("type") == "error":
                # Do not surface Pi's error string: providers sometimes
                # include configuration paths or authentication detail there.
                raise PiError("Pi Coding Agent failed to complete the request.")
            message = event.get("message")
            if isinstance(message, dict) and message.get("role") == "assistant":
                content = message.get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    texts.extend(part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text")
            elif event.get("type") in {"assistant", "assistant_message"}:
                text = event.get("text") or event.get("content")
                if isinstance(text, str):
                    texts.append(text)
        answer = "\n".join(part.strip() for part in texts if part and part.strip()).strip()
        return answer or None
