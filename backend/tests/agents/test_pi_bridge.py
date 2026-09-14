import subprocess

import pytest

from app.agents.pi import PiBridge, PiError


def test_pi_bridge_extracts_assistant_result(monkeypatch):
    def fake_run(*args, **kwargs):
        assert "--mode" in args[0]
        assert "rpc" in args[0]
        assert '"type": "prompt"' in kwargs["input"]
        return subprocess.CompletedProcess(
            args[0], 0,
            '{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"planned"}]}}\n',
            "",
        )

    monkeypatch.setattr("app.agents.pi.subprocess.run", fake_run)
    result = PiBridge(command="pi", provider="ollama", model="tool-model").run("safe prompt")
    assert result.text == "planned"
    assert result.provider == "ollama"


def test_pi_bridge_rejects_malformed_response(monkeypatch):
    monkeypatch.setattr(
        "app.agents.pi.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "not json\n", ""),
    )
    with pytest.raises(PiError, match="unexpected response"):
        PiBridge().run("prompt")


def test_pi_bridge_handles_rpc_error_event(monkeypatch):
    monkeypatch.setattr(
        "app.agents.pi.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, '{"type":"response","success":false,"error":"secret detail"}\n', ""
        ),
    )
    with pytest.raises(PiError, match="failed to complete"):
        PiBridge().run("prompt")


def test_pi_bridge_handles_unavailable_executable(monkeypatch):
    monkeypatch.setattr("app.agents.pi.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    with pytest.raises(PiError, match="unavailable"):
        PiBridge().run("prompt")


def test_pi_bridge_handles_timeout(monkeypatch):
    monkeypatch.setattr("app.agents.pi.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("pi", 1)))
    with pytest.raises(PiError, match="timed out"):
        PiBridge(timeout_seconds=1).run("prompt")
