import json

import pytest

from cv_toolkit import jev_review_cli as cli
from cv_toolkit.jev_review import transport


def test_disabled_does_not_read_packet_or_credentials(monkeypatch, capsys):
    def forbidden(*args):
        raise AssertionError("credential accessed")

    monkeypatch.setattr(cli.os.environ, "get", forbidden)
    assert cli.main(["missing.json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


def test_consent_before_packet_or_credentials(monkeypatch, capsys):
    def forbidden(*args):
        raise AssertionError("credential accessed")

    monkeypatch.setattr(cli.os.environ, "get", forbidden)
    assert cli.main(["missing.json", "--enable"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "needs_consent"


def test_missing_packet_is_structured(capsys):
    assert cli.main(["missing.json", "--enable", "--allow-external-review"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_approved_synthetic_call(tmp_path, monkeypatch, capsys):
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "document": "cover_letter",
                "unit_id": "p1",
                "claim": "Built tests.",
                "evidence": "Built tests.",
                "snapshot": "r1",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    calls = []

    def factory(provider, key):
        assert key == "synthetic-token"

        def send(body):
            calls.append(body)
            return {"model": "pinned", "answers": {"supported": {"type": "noul", "noul": 0.97}}}

        return send

    monkeypatch.setattr(cli, "transport", factory)
    assert cli.main(
        [str(packet), "--enable", "--allow-external-review", "--model", "pinned", "--validated-model", "pinned"]
    ) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["advisory"] and receipt["route"] == "host_review"
    assert "synthetic-token" not in json.dumps(receipt)
    assert len(calls) == 1


def test_cli_rejects_oversized_packet(tmp_path, capsys):
    packet = tmp_path / "large.json"
    packet.write_bytes(b"x" * 24_001)
    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_cli_rejects_deep_json_as_invalid_input(tmp_path, capsys, monkeypatch):
    packet = tmp_path / "nested.json"
    packet.write_bytes(("[" * 1100 + "0" + "]" * 1100).encode("ascii"))
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    monkeypatch.setattr(cli, "transport", lambda *args: (_ for _ in ()).throw(AssertionError("sent")))
    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_cli_rejects_lone_surrogate_packet_without_sending(tmp_path, capsys, monkeypatch):
    packet = tmp_path / "surrogate.json"
    packet.write_bytes(
        b'{"document":"resume","unit_id":"u1","claim":"x",'
        b'"evidence":"\\ud800","snapshot":"r1"}'
    )
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    calls = []
    monkeypatch.setattr(cli, "transport", lambda *args: calls.append(args))
    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_packet"
    assert calls == []


def test_cli_reports_malformed_model_config_as_serializable_invalid_config(tmp_path, capsys, monkeypatch):
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({
        "document": "resume", "unit_id": "u1", "claim": "x",
        "evidence": "x", "snapshot": "r1",
    }), encoding="utf-8")
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    monkeypatch.setattr(cli, "transport", lambda *args: (_ for _ in ()).throw(AssertionError("sent")))
    assert cli.main([
        str(packet), "--enable", "--allow-external-review", "--model", "\ud800",
    ]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "invalid_config"


@pytest.mark.parametrize("probability", [10**1000, -(10**1000)])
def test_cli_reports_huge_provider_probability_as_invalid_response(tmp_path, capsys, monkeypatch, probability):
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({
        "document": "resume", "unit_id": "u1", "claim": "x",
        "evidence": "x", "snapshot": "r1",
    }), encoding="utf-8")
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    calls = []

    def factory(provider, key):
        def send(body):
            calls.append(body)
            return {"model": "pinned", "answers": {"supported": {"type": "noul", "noul": probability}}}

        return send

    monkeypatch.setattr(cli, "transport", factory)
    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "invalid_response"
    assert len(calls) == 1


def test_cli_reports_deep_provider_json_as_invalid_response_without_retry(tmp_path, capsys, monkeypatch):
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({
        "document": "resume", "unit_id": "u1", "claim": "x",
        "evidence": "x", "snapshot": "r1",
    }), encoding="utf-8")
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    attempts = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return ("[" * 1100 + "0" + "]" * 1100).encode("ascii")

    class Opener:
        def open(self, request, timeout):
            attempts.append(request)
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    monkeypatch.setattr(cli, "transport", transport)

    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "invalid_response"
    assert len(attempts) == 1


@pytest.mark.parametrize("raw", [b"not JSON", b"\xff", b"x" * 65_537], ids=["malformed", "undecodable", "oversized"])
def test_cli_reports_invalid_provider_payload_without_retry(tmp_path, capsys, monkeypatch, raw):
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({
        "document": "resume", "unit_id": "u1", "claim": "x",
        "evidence": "x", "snapshot": "r1",
    }), encoding="utf-8")
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-token")
    attempts = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert limit == 65_537
            return raw

    class Opener:
        def open(self, request, timeout):
            attempts.append(request)
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    monkeypatch.setattr(cli, "transport", transport)

    assert cli.main([str(packet), "--enable", "--allow-external-review"]) == 3
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "invalid_response"
    assert result["advisory"] is True and result["route"] == "host_review"
    assert "synthetic-token" not in output
    assert "not JSON" not in output
    assert len(attempts) == 1
