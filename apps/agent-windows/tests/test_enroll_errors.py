import httpx

from orqelis_agent.cli import main


class _Boom:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def enroll(self, _code: str) -> dict:
        raise self.exc


def test_enroll_timeout_is_not_a_traceback(monkeypatch, capsys):
    monkeypatch.setattr("orqelis_agent.cli.AgentClient", lambda _config: _Boom(httpx.ReadTimeout("timed out")))
    assert main(["enroll", "--code", "123456", "--api", "https://api.orqelis.example"]) == 1
    err = capsys.readouterr().err
    assert "Could not reach the Orqelis API" in err
    assert "Traceback" not in err


def test_enroll_server_error_is_not_a_traceback(monkeypatch, capsys):
    monkeypatch.setattr("orqelis_agent.cli.AgentClient", lambda _config: _Boom(RuntimeError("server 503")))
    assert main(["enroll", "--code", "123456", "--api", "https://api.orqelis.example"]) == 1
    err = capsys.readouterr().err
    assert "failed: server 503" in err
    assert "Traceback" not in err
