#!/usr/bin/env python3
"""Probe one direction of an A2A link: Agent Card fetch, then an optional authenticated
JSON-RPC `message/send`. Stdlib only; prints status metadata and never the credential.

    python3 probe_a2a_peer.py http://peer-host:9900                    # card only
    A2A_TOKEN=$(...) python3 probe_a2a_peer.py http://peer-host:9900 \
        --token-env A2A_TOKEN --text "direction test"

Supply the bearer value through the environment and name it with --token-env: the value is
read from os.environ at call time, so it stays out of argv, shell history and any transcript
this tool writes. Set --token-env to the name of the variable holding the token YOU present to
that peer (the outbound one), not the one you accept from it.

Reading the result, as a classification rather than a yes/no:

  card 200 + send 200            the peer accepted this caller's credential
  card 200 + send 401 / -32050   reachable, credential rejected: the peer's trust table does not
                                 carry this caller's identity name, or a shared secret-manager
                                 project has overwritten the peer's own values
  card 200 + send timeout        the peer is reachable but its agent did not answer in time
  card refused (ECONNREFUSED)    path exists, nothing listening: start or publish the peer port
  card timed out                 no path to the peer at all

The adapter also accepts `SendMessage` and `message/stream`; this script uses `message/send`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

CARD_PATH = "/.well-known/agent-card.json"


def fetch_card(base: str, timeout: float) -> tuple[int | None, str]:
    url = base.rstrip("/") + CARD_PATH
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(1000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - reported as a classification
        return None, f"{type(exc).__name__}: {exc}"


def send_message(base: str, token: str, text: str, timeout: float) -> tuple[int | None, str]:
    payload = {
        "jsonrpc": "2.0",
        "id": f"probe-{int(time.time())}",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": f"probe-{int(time.time())}",
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/", data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", help="peer base URL, e.g. http://100.x.y.z:9900")
    ap.add_argument("--token-env", default="A2A_TOKEN",
                    help="env var NAME holding the outbound token (default: A2A_TOKEN)")
    ap.add_argument("--text", default="Lana direction probe. Reply with: pong",
                    help="text of the probe message")
    ap.add_argument("--timeout", type=float, default=150.0,
                    help="seconds to wait for the peer agent's answer (default 150)")
    args = ap.parse_args()

    status, body = fetch_card(args.url, timeout=20.0)
    if status is None:
        print(f"card  : NO PATH - {body}")
        return 1
    print(f"card  : HTTP {status}")
    if status == 200:
        try:
            card = json.loads(body)
            print(f"        name={card.get('name')!r} url={card.get('url')!r}")
        except ValueError:
            print("        (card body was not JSON)")

    token = os.environ.get(args.token_env, "")
    if not token:
        print(f"send  : skipped - {args.token_env} is unset in this environment")
        return 0 if status == 200 else 1

    code, reply = send_message(args.url, token, args.text, args.timeout)
    if code is None:
        print(f"send  : UNANSWERED - {reply}")
        return 1
    print(f"send  : HTTP {code}")
    if code == 401 or "-32050" in reply:
        print("        credential rejected - check the peer's A2A_PEER_TOKENS /")
        print("        A2A_TRUSTED_PEERS carry THIS caller's identity name (lowercase,")
        print("        exact match), and that no shared project is overriding them")
        return 1
    if code == 200:
        try:
            data = json.loads(reply)
            if data.get("error"):
                print(f"        jsonrpc error: {data['error']}")
                return 1
            result = data.get("result") or {}
            tid = result.get("id") or (result.get("task") or {}).get("id")
            print(f"        accepted; task id={tid!r}")
        except ValueError:
            print("        (reply body was not JSON)")
        return 0
    print(f"        unexpected status; body head: {reply[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
