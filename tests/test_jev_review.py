import copy
import json
import math
import urllib.error

import pytest

from cv_toolkit.jev_review import NoRedirect, review, transport


PACKET = {
    "document": "resume",
    "unit_id": "u1",
    "claim": "Built a Python test bench.",
    "evidence": "I built a Python test bench.",
    "snapshot": "revision-1",
}


def response(p=0.96, model="pinned-model"):
    return {"model": model, "answers": {"supported": {"type": "noul", "noul": p}}}


def invoke(packet=None, send=None, **kw):
    options = dict(
        enabled=True,
        authorized=True,
        model="alias",
        validated_model="pinned-model",
        send=send or (lambda body: response()),
    )
    options.update(kw)
    return review(PACKET if packet is None else packet, **options)


def test_disabled_and_unauthorized_never_send():
    def forbidden(body):
        pytest.fail("unexpected network")

    assert invoke(send=forbidden, enabled=False)["status"] == "disabled"
    assert invoke(send=forbidden, authorized=False)["status"] == "needs_consent"


@pytest.mark.parametrize("p,signal", [(0.96, "supported"), (0.04, "concern"), (0.5, "uncertain")])
def test_signal_is_not_approval(p, signal):
    result = invoke(send=lambda body: response(p))
    assert result["signal"] == signal
    assert result["advisory"] is True and result["route"] == "host_review"
    assert result["confidence_source"] == "derived"
    assert result["confidence"] == pytest.approx(max(p, 1 - p))
    assert "approved" not in result and "pass" not in result


@pytest.mark.parametrize(
    "p",
    [True, None, "0.9", -0.1, 1.1, float("nan"), float("inf"), 10**1000, -(10**1000)],
)
def test_invalid_probability(p):
    assert invoke(send=lambda body: response(p))["status"] == "invalid_response"


@pytest.mark.parametrize(
    "bad", [{}, {"model": "x", "answers": {}}, {"model": "", "answers": {}}, []]
)
def test_malformed_response(bad):
    assert invoke(send=lambda body: bad)["status"] == "invalid_response"


def test_lone_surrogate_packet_is_invalid_without_sending():
    calls = []
    packet = dict(PACKET, evidence="\ud800")
    result = invoke(packet, send=lambda body: calls.append(body))
    assert result["status"] == "invalid_packet"
    assert calls == []


def test_valid_unicode_packet_is_reviewable():
    packet = dict(
        PACKET,
        unit_id="résumé-日本語",
        claim="Built a café test bench — déjà vu.",
        evidence="I built the café test bench for 日本語 users.",
    )
    result = invoke(packet, send=lambda body: response())
    assert result["status"] == "ok"


@pytest.mark.parametrize("field", ["model", "validated_model"])
def test_malformed_model_configuration_is_serializable_and_not_sent(field):
    calls = []
    options = {"send": lambda body: calls.append(body), field: "\ud800"}
    result = invoke(**options)
    assert result["status"] == "invalid_config"
    assert json.dumps(result, ensure_ascii=False, allow_nan=False)
    assert calls == []


def test_non_string_validated_model_is_invalid_config():
    result = invoke(validated_model=None, send=lambda body: pytest.fail("unexpected send"))
    assert result["status"] == "invalid_config"


def test_malformed_resolved_model_is_invalid_response():
    result = invoke(
        send=lambda body: {"model": "\ud800", "answers": {"supported": {"type": "noul", "noul": 0.9}}}
    )
    assert result["status"] == "invalid_response"


def test_drift_stays_advisory():
    result = invoke(send=lambda body: response(model="new-model"))
    assert result["version_drift"] is True and result["route"] == "host_review"


def test_request_shape_and_snapshot_binding():
    requests = []

    def send(body):
        requests.append(body)
        return response()

    result = invoke(send=send)
    assert set(requests[0]) == {"state", "model", "questions"}
    assert requests[0]["questions"]["supported"]["type"] == "noul"
    other = copy.deepcopy(PACKET)
    other["evidence"] = "I only observed the test bench."
    assert invoke(other)["packet_hash"] != result["packet_hash"]
    letter = dict(PACKET, document="cover_letter")
    assert invoke(letter)["status"] == "ok"


@pytest.mark.parametrize(
    "packet",
    [
        dict(PACKET, extra="private"),
        dict(PACKET, claim=""),
        dict(PACKET, evidence="a" * 24001),
        dict(PACKET, evidence="é" * 24001),
    ],
)
def test_bad_packet_never_send(packet):
    def forbidden(body):
        pytest.fail("unexpected network")

    assert invoke(packet, send=forbidden)["status"] == "invalid_packet"


def test_failure_does_not_echo_exception():
    def fail(body):
        raise TimeoutError("sensitive outbound body")

    result = invoke(send=fail)
    assert result["status"] == "unavailable"
    assert "sensitive" not in str(result)


def test_transport(monkeypatch):
    calls = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert limit == 65537
            return json.dumps(response()).encode()

    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert timeout == 10
            assert request.full_url == "https://openrouter.ai/api/alpha/decisions"
            assert request.get_header("Authorization") == "Bearer synthetic-token"
            assert "synthetic-token" not in request.data.decode()
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    assert transport("openrouter", "synthetic-token")({"state": "synthetic"})["model"]
    assert len(calls) == 1


def test_redirect_refused():
    assert NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid") is None


def test_oversized_response(monkeypatch):
    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return b"x" * limit

    class Opener:
        def open(self, request, timeout):
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    with pytest.raises(ValueError):
        transport("typesafe", "synthetic-token")({})


@pytest.mark.parametrize("provider", ["unknown", "http://local.invalid"])
def test_no_arbitrary_provider(provider):
    with pytest.raises(ValueError):
        transport(provider, "synthetic-token")


def test_transport_does_not_retry(monkeypatch):
    attempts = 0

    class Opener:
        def open(self, request, timeout):
            nonlocal attempts
            attempts += 1
            raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    sender = transport("typesafe", "synthetic-token")
    with pytest.raises(urllib.error.URLError):
        sender({})
    assert attempts == 1


def test_deep_provider_json_is_invalid_without_retry(monkeypatch):
    attempts = 0

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return ("[" * 1100 + "0" + "]" * 1100).encode("ascii")

    class Opener:
        def open(self, request, timeout):
            nonlocal attempts
            attempts += 1
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    result = invoke(send=transport("typesafe", "synthetic-token"))
    assert result["status"] == "invalid_response"
    assert attempts == 1


@pytest.mark.parametrize("raw", [b"not JSON", b"\xff", b"x" * 65_537], ids=["malformed", "undecodable", "oversized"])
def test_invalid_provider_payload_is_invalid_without_retry(monkeypatch, raw):
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
    result = invoke(send=transport("typesafe", "synthetic-token"))
    assert result["status"] == "invalid_response"
    assert result["advisory"] is True and result["route"] == "host_review"
    assert "synthetic-token" not in str(result)
    assert "not JSON" not in str(result)
    assert len(attempts) == 1


@pytest.mark.parametrize("error", [TimeoutError("sensitive timeout"), urllib.error.URLError("sensitive network")])
@pytest.mark.parametrize("stage", ["open", "read"])
def test_transport_failure_is_unavailable_without_retry(monkeypatch, error, stage):
    attempts = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            raise error

    class Opener:
        def open(self, request, timeout):
            attempts.append(request)
            if stage == "open":
                raise error
            return Reply()

    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    result = invoke(send=transport("typesafe", "synthetic-token"))
    assert result["status"] == "unavailable"
    assert result["advisory"] is True and result["route"] == "host_review"
    assert "sensitive" not in str(result)
    assert len(attempts) == 1


def test_unicode_malformed_response_is_invalid():
    result = invoke(send=lambda body: {"model": "pinned", "answers": {"supported": {"type": "noul", "noul": "é"}}})
    assert result["status"] == "invalid_response"


def test_stale_packet_identity_is_visible():
    first = invoke()
    changed = dict(PACKET, snapshot="revision-2")
    second = invoke(changed)
    assert first["packet_hash"] != second["packet_hash"]
    assert first["request_hash"] != second["request_hash"]
    assert second["advisory"] is True
