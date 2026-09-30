# Agent-to-agent links across machines

Two transports ship in the same build. Pick deliberately.

| | A2A platform (`plugins/platforms/a2a/`) | `hermes peer` (bot-to-bot DM) |
|---|---|---|
| What it is | Open A2A v1.0 protocol: Agent Card discovery, JSON-RPC `SendMessage`, SSE streaming, push callbacks; interoperates with non-Hermes agents | One synchronous turn into the peer's canonical "Bot Chat" over the peer's `api_server` platform |
| Config | `platforms.a2a.enabled`, `platforms.a2a.extra.port`; outbound peers in `a2a_agents` | URL in `config.yaml` → `bot_peers.<name>.url`; key in env as `HERMES_PEER_<NAME>_KEY` |
| Where the credential lives | Caller's outbound peer token sits inline in `a2a_agents.<name>.auth.token`, so reference it as `"${ENV_VAR}"` | Key resolved from the secret store first, then raw env — it never has to touch `config.yaml` |
| Reachability | Each direction needs the *callee* dialable by the caller | Same |
| Extras | Agent Card, audit log, per-peer identity, ping-pong cap, injection filtering | The lightest thing that works between two Hermes boxes |

Prefer A2A when either agent must be discoverable or callable by non-Hermes frameworks. Prefer `hermes peer` when both ends are Hermes and the peer key must stay out of `config.yaml`.

## A2A enablement, verified on a containerized deployment

Config, always through the CLI — never by hand-editing `config.yaml`:

```bash
hermes config set platforms.a2a.enabled true
hermes config set platforms.a2a.extra.port 9900
hermes config set a2a_agents.<peer>.url http://<host>:9900
hermes config set a2a_agents.<peer>.auth.type bearer
hermes config set a2a_agents.<peer>.auth.token '${A2A_PEER_TOKEN_VAR}'   # single-quote: the file must keep the literal ${...}
hermes config set a2a_agents.<peer>.timeout 300
```

- The platform section is top-level `platforms:` (the same place `telegram` lives). `gateway.platforms` is not where this deployment's platforms are read from.
- `hermes config set` prints a "Did you mean …" notice for nested paths outside its known schema and may still write them — confirm with `hermes config get <key>` rather than trusting the notice. Each write also snapshots to `backups/config/config.yaml.good.<timestamp>`.
- The config loader expands `${VAR}` references, which is what keeps the outbound peer token in the secret manager instead of plaintext on disk.

Environment-only knobs — the adapter reads these through the secret scope, not from `extra`: `A2A_HOST`, `A2A_PEER_TOKENS`, `A2A_BEARER_TOKEN`, `A2A_TRUSTED_PEERS`, `A2A_AGENT_NAME`, `A2A_PUBLIC_URL`, `A2A_ADVERTISED_TOOLSETS`. `extra` accepts only `port`, `advertised_toolsets`, `agents`/`served_agents`, and an `A2A_PORT` env value wins over `extra.port`.

Tokens:

- Per-peer is the preferred shape: `A2A_PEER_TOKENS="<peer>:<token>,<other>:<token>"`, with `A2A_TRUSTED_PEERS=<peer>` as an allow-list. The matched name — never anything in the request body — drives rate limiting, trust, and audit.
- Give each direction its own token (one for peer→you, one for you→peer). One shared value means one leak opens both directions.
- **With no token of any kind the adapter refuses to widen: it binds `127.0.0.1` and ignores `A2A_HOST`.** Lean on that property when reporting risk — enabling the platform before the secrets exist cannot expose the agent, even across an unplanned restart.

Outbound client tools register with `hermes tools enable a2a --platform cli|telegram|a2a` (`a2a_discover`, `a2a_call`, `a2a_list`, `a2a_history`, `a2a_orchestrate`).

Activation: the platform starts with the gateway, so nothing is live until a restart. Verify the live platform list in `gateway_state.json` and probe the port before reporting success.

## Configuring the answering side (interactive wizard)

`hermes gateway setup` → A2A walks the operator through the inbound surface. Prompt order, and what each answer should be:

| Prompt | Answer |
|---|---|
| `Inbound A2A port (default 9900)` | the port, or blank — blank is safe because the adapter's own fallback *is* 9900 |
| `Agent name to advertise (blank = hostname-derived)` | the display name; blank makes the card advertise the hostname |
| `Configure tokens to allow REMOTE A2A peers? [y/N]` | `y` — this is the switch that widens the bind |
| `Per-peer tokens (name:token, …)` | `<caller>:<token>`, named with the **caller's** identity |
| `Shared bearer token (blank to skip)` | blank |
| `Bind host for remote access (e.g. 0.0.0.0)` | the tailnet address, or `0.0.0.0` |

- **The wizard never asks for `A2A_PUBLIC_URL` or `A2A_TRUSTED_PEERS`.** Append both to the answering side's `.env` by hand and restart, or the Agent Card advertises its bind address (`127.0.0.1`) to every peer that discovers it.
- **Leave the shared bearer token blank.** `A2A_BEARER_TOKEN` degrades the caller's identity to `ip:<addr>`, which costs per-peer rate limiting, trust, and audit attribution — and is *then* rejected by `A2A_TRUSTED_PEERS=<name>` when an allow-list is set, since an `ip:` identity is not the peer's name. That yields a failure which looks like a bug while the token itself is perfectly valid.
- **Identity names are matched exactly and case-sensitively** (a plain string membership test against the allow-list). Keep identities lowercase (`lana`, `mila`) and use the capitalised form only as the advertised display name — `Mila` in the token entry against `mila` in the allow-list silently rejects every authenticated call.
- **The per-peer token prompt is not masked**; the value is echoed to the terminal. Watch the operator's scrollback, and never move the value back through chat.
- **The bind address is the proof.** `ss -ltnp | grep <port>` must show the tailnet address or `0.0.0.0`, never `127.0.0.1`. Still seeing `127.0.0.1` after entering a token means the env did not reach the process — wrong home or profile, or the answer was never saved. Check the home's `.env` for the variable *names* only (`grep -oE '^A2A_[A-Z_]+' <home>/.env | sort`, never the values) and the gateway journal for `A2A_HOST=… ignored — no token`.
- The wizard writes env only; the port stays bound where it was until the gateway restarts, so a restart is part of the step, not an afterthought. A machine with no secret-manager integration keeps its peer token in `.env` in plaintext — say so rather than implying it is protected.

## Reachability decides the topology — test it before writing config

Whoever *calls* must be able to dial whoever *answers*, and each direction needs proving separately from the container that will actually make the call.

Run `scripts/probe_reachability.py <host:port> …` and read the result as a classification, not a yes/no:

| Result | Meaning | Action |
|---|---|---|
| OPEN | a listener is there | proceed |
| refused (`ECONNREFUSED`) | path exists, nothing listening | the network is fine — start or publish the service |
| timed out (`EAGAIN`) | no path — node offline or firewalled | fix the path before touching config |

- A container usually reaches the tailnet *outbound* even when nothing can reach *in*. Prove it with a known-open tailnet port before assuming either way; a refusal on one host-published port is not evidence that the network is broken.
- `getent hosts <node>.<tailnet>.ts.net` resolves node IPs from inside the container when `/etc/resolv.conf` carries the tailnet search domain and Docker's embedded resolver forwards to MagicDNS. Cheapest way to turn a name you were given into an address you can probe.
- **A resolved name is neither proof of liveness nor proof of currency.** MagicDNS answers for every *registered* device — powered-off machines and obsolete records nobody deleted alike. Two consequences: resolution only proves a record exists, and **a name that is not in the tailnet's own device list is a stale record, not the machine you want.** Get the machine's identity from `tailscale status` on the host or the admin console's Machines page, then probe that address. Guessing candidate names and probing whichever one resolves manufactures a confident, wrong "the peer is offline" out of a deleted ghost, and any config value already keyed to that name (a hardcoded peer URL) is silently wrong from then on.
- **A peer that resolves while every port times out is offline, not misconfigured** — do not go hunting for a firewall or a bad token in that state. Read the probe's classification instead: `refused` means the node is up and answering with nothing listening (so the network is fine and the service needs starting or publishing), while a timeout means there is no path at all.
- **Inbound needs a host-level published port, because a container's ports are not on the tailnet.** With no Docker socket or host SSH keys available in the container, that step belongs to the user — hand it over as an exact command. Bind the publish to the tailnet address (`100.x.y.z:9900:9900`), not `0.0.0.0`, so the service never appears on the public IP.
- Do not route a peer link over a public dashboard hostname when the deployment's design keeps machine traffic tailnet-only.

## Handshake secrets

Each direction needs its own token, and each side ends up holding two values: one it *accepts*, one it *presents*.

| Token | Authenticates | Answering side stores | Calling side presents |
|---|---|---|---|
| `T_peer` | peer → you | `A2A_PEER_TOKENS="<peer>:T_peer"` on your side | `a2a_agents.<you>.auth.token = T_peer` on the peer |
| `T_you` | you → peer | `A2A_PEER_TOKENS="<you>:T_you"` on the peer | `a2a_agents.<peer>.auth.token = "${A2A_PEER_TOKEN_VAR}"` |

- Exactly one value has to be entered on the other machine, and it cannot be moved from the side that generated it without the operator carrying it out of the vault UI. Fill one side completely, then hand over the other side's half.
- Store each direction's token in the deployment's secret manager, and let the user move the value to the other machine from the vault UI. Never print a token into chat to "copy it over".
- When a secret is created for a *different* machine, expect the integration to inject it here anyway: the project supplies the env of whichever deployment holds the project token. Confirm a stray key's purpose by comparing fingerprints against the value it should match, not by assuming the name is wrong.
- **A shared project does not merely leak a token — it overwrites the peer's env with your trust table.** If the peer's box holds a machine account for your project, it boots with *your* `A2A_PEER_TOKENS="<your-peer>:…"` and `A2A_TRUSTED_PEERS="<your-peer>"`: your identity names. The peer therefore accepts and trusts the wrong principal, and every authenticated call in the *you → peer* direction answers `401` / JSON-RPC `-32050 unauthorized` no matter what the peer changes locally, because project values override a local `.env`. Diagnose this by reading the peer's *effective* identity names, not by rotating tokens a third time.
- **Repair by scoping, never by granting.** Give each machine its own project and machine account, holding its own `A2A_PEER_TOKENS="<caller>:<T>"`, `A2A_TRUSTED_PEERS="<caller>"`, `A2A_AGENT_NAME`, `A2A_HOST`, `A2A_PORT`, `A2A_PUBLIC_URL`; then revoke that account's access to the other machine's project. A read-only machine account can read secrets but not replace them, which is exactly why the peer cannot fix an overridden value from its own side — and why a peer's request for write access to the shared project must be refused: write access lets that machine rewrite your platform token, model-provider keys and dashboard credential.
- **A peer's "token aligned" / "fixed" message is a self-report, not a verification.** After any such claim, re-run the authenticated call in the affected direction and report the measured status — a peer can be running a stale or overridden env and believe its edit took effect.

## Checklist

1. The peer machine answers from the caller (probe above).
2. The inbound port is published and bound to the tailnet address.
3. Platform enabled, port set, `A2A_PUBLIC_URL` pointing at the address peers can actually call.
4. Per-peer tokens in the secret manager; `${VAR}` reference in `config.yaml` for the outbound token.
5. Restart, then verify: platform present in `gateway_state.json`, port open, Agent Card fetchable at `/.well-known/agent-card.json`, audit file written on the first exchange.
6. Prove **each direction separately** with an authenticated round-trip: `scripts/probe_a2a_peer.py <url> --token-env <VAR>` issues one JSON-RPC `message/send` and classifies the answer (`401`/`-32050` = the peer's trust table does not carry this caller's identity; HTTP 200 with a task id = the direction works). A card fetch is unauthenticated and proves nothing about the handshake.
