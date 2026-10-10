"""Explicit optional external evidence review, separate from release."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .jev_review import _validation_status, review, transport


def _emit(status, code):
    print(json.dumps({"advisory": True, "route": "host_review", "status": status}))
    return code


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if "--enable" not in raw_argv:
        return _emit("disabled", 0)
    if "--allow-external-review" not in raw_argv:
        return _emit("needs_consent", 2)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet")
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--allow-external-review", action="store_true")
    parser.add_argument("--provider", choices=["typesafe", "openrouter"], default="typesafe")
    parser.add_argument("--model")
    parser.add_argument("--validated-model", default="")
    parser.add_argument("--credential-env")
    args = parser.parse_args(argv)

    try:
        with Path(args.packet).open("rb") as source:
            raw = source.read(24_001)
        if len(raw) > 24_000:
            return _emit("invalid_input", 2)
        packet = json.loads(raw.decode("utf-8"))
        if not isinstance(packet, dict):
            return _emit("invalid_input", 2)
    except (OSError, UnicodeError, ValueError, RecursionError):
        return _emit("invalid_input", 2)

    validation_status = _validation_status(packet, args.model or ("jev-latest" if args.provider == "typesafe" else "typesafe/jev-1.13"), args.validated_model)
    if validation_status:
        return _emit(validation_status, 2)

    credential_name = args.credential_env or (
        "TYPESAFE_API_KEY" if args.provider == "typesafe" else "OPENROUTER_API_KEY"
    )
    key = os.environ.get(credential_name)
    if not key:
        return _emit("missing_credential", 2)
    model = args.model or ("jev-latest" if args.provider == "typesafe" else "typesafe/jev-1.13")
    try:
        sender = transport(args.provider, key)
        result = review(
            packet,
            enabled=True,
            authorized=True,
            model=model,
            validated_model=args.validated_model,
            send=sender,
        )
    except (OSError, ValueError):
        return _emit("unavailable", 3)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    if result["status"] == "ok":
        return 0
    return 3 if result["status"] in {"unavailable", "invalid_response"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
