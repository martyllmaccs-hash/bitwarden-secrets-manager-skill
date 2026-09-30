#!/usr/bin/env python3
"""TCP reachability probe for cross-machine links.

Answers the one question that decides whether an agent-to-agent link can work:
which host:port pairs are actually dialable from THIS machine. Prints a
classification, not a yes/no, because "refused" and "timed out" mean opposite
things — refused means the network path is fine and nothing is listening (fix
the service), timed out means there is no path at all (fix the network).

Usage:
    python3 probe_reachability.py HOST:PORT [HOST:PORT ...]
    python3 probe_reachability.py --timeout 2 100.64.0.5:9900 p1.tailnet.ts.net:22

Notes:
  * Prefer hostnames where the tailnet/MagicDNS name resolves; printing the
    resolved address alongside the name makes a stale address obvious.
  * Run it from the container that will make the real call, not from the host.
  * A resolved name is NOT a live node: MagicDNS answers for every registered
    device, powered-off ones included. Resolution only yields the address; the
    verdict below is what decides whether the link can work.
  * Stdlib only; safe to run anywhere Python 3 exists.
"""

from __future__ import annotations

import argparse
import socket
import sys

REFUSED = {
    61: "refused (path works, no listener)",   # macOS
    111: "refused (path works, no listener)",  # Linux
}
NO_PATH = {
    110: "TIMEOUT (no path)",      # Linux ETIMEDOUT
    113: "unreachable (no path)",  # Linux EHOSTUNREACH
    11: "TIMEOUT (no path)",       # EAGAIN, as reported for filtered tailnet peers
}


def probe(host: str, port: int, timeout: float) -> tuple[int | None, str, str]:
    """Return (errno, verdict, resolved-address)."""
    try:
        resolved = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)[0][4][0]
    except OSError as exc:
        return None, f"DNS FAILED ({exc})", "-"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        rc = sock.connect_ex((resolved, port))
    except OSError as exc:
        return None, f"error: {exc}", resolved
    finally:
        sock.close()

    if rc == 0:
        return rc, "OPEN", resolved
    if rc in REFUSED:
        return rc, REFUSED[rc], resolved
    if rc in NO_PATH:
        return rc, NO_PATH[rc], resolved
    return rc, f"errno {rc}", resolved


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="+", metavar="HOST:PORT")
    parser.add_argument("--timeout", type=float, default=4.0,
                        help="per-target connect timeout in seconds (default 4)")
    args = parser.parse_args(argv)

    rows: list[tuple[str, str, str]] = []
    for target in args.targets:
        host, _, port_text = target.rpartition(":")
        if not host or not port_text.isdigit():
            rows.append((target, "-", "bad target, expected HOST:PORT"))
            continue
        _, verdict, resolved = probe(host, int(port_text), args.timeout)
        rows.append((target, resolved, verdict))

    width = max(len(r[0]) for r in rows)
    for target, resolved, verdict in rows:
        print(f"{target:<{width}}  {resolved:<16} -> {verdict}")

    # Exit 0 only when everything answered; callers use this to gate config work.
    return 0 if all(r[2] == "OPEN" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
